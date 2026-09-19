"""
Vehicle entry / exit orchestration.

DATA STRUCTURES
  - Hash table (_active_sessions_cache): plate -> session_id for O(1) lookup.
  - Queue (via AllocationService): fair bay allocation.

TRANSACTIONS
  Entry wraps "get-or-create vehicle + allocate bay + create session" in
  ONE commit so we never end up with a bay marked OCCUPIED but no session.
"""
import re
from datetime import datetime
from ..extensions import db
from ..models.vehicle import Vehicle
from ..models.parking_session import ParkingSession, SessionStatus
from ..models.payment import Payment, PaymentStatus
from .allocation_service import BayAllocationService
from .fee_service import FeeCalculationService
from .audit_service import AuditService

# Kenya plate: 2-3 letters, optional space, 3 digits, optional letter.
PLATE_REGEX = re.compile(r"^[A-Z]{2,3}\s?\d{3}[A-Z]?$")


class ParkingService:
    # Hash table: normalised plate -> session_id
    _active_sessions_cache = {}

    @staticmethod
    def normalise_plate(plate):
        return re.sub(r"\s+", "", plate or "").upper()

    @classmethod
    def validate_plate(cls, plate):
        return bool(PLATE_REGEX.match((plate or "").upper().strip()))

    @classmethod
    def get_active_session_by_plate(cls, plate):
        key = cls.normalise_plate(plate)
        sid = cls._active_sessions_cache.get(key)
        if sid:
            s = db.session.get(ParkingSession, sid)
            if s and s.is_active:
                return s
            cls._active_sessions_cache.pop(key, None)

        vehicle = Vehicle.query.filter_by(number_plate=key).first()
        if not vehicle:
            return None
        s = (ParkingSession.query
             .filter(ParkingSession.vehicle_id == vehicle.id,
                     ParkingSession.status.in_([SessionStatus.ACTIVE,
                                                SessionStatus.PAYMENT_PENDING,
                                                SessionStatus.PAID])).first())
        if s:
            cls._active_sessions_cache[key] = s.id
        return s

    @staticmethod
    def generate_ticket_number():
        today = datetime.utcnow().strftime("%Y%m%d")
        n = ParkingSession.query.filter(
            ParkingSession.ticket_number.like(f"PK-{today}-%")).count() + 1
        return f"PK-{today}-{n:05d}"

    @classmethod
    def register_entry(cls, plate, user_id=None, vehicle_type="car"):
        plate_norm = cls.normalise_plate(plate)
        if not cls.validate_plate(plate_norm):
            return {"ok": False, "reason": "INVALID_PLATE",
                    "message": "Number plate format is invalid (e.g. KDA 123A)."}
        if cls.get_active_session_by_plate(plate_norm):
            return {"ok": False, "reason": "DUPLICATE_ACTIVE",
                    "message": f"Vehicle {plate_norm} already has an active session."}
        try:
            vehicle = Vehicle.query.filter_by(number_plate=plate_norm).first()
            if not vehicle:
                vehicle = Vehicle(number_plate=plate_norm, vehicle_type=vehicle_type)
                db.session.add(vehicle)
                db.session.flush()

            bay = BayAllocationService.allocate_bay()
            if bay is None:
                db.session.rollback()
                return {"ok": False, "reason": "NO_AVAILABLE_SPACE",
                        "message": "Parking lot is full."}
            BayAllocationService.mark_occupied(bay)

            session = ParkingSession(
                ticket_number=cls.generate_ticket_number(),
                vehicle_id=vehicle.id, bay_id=bay.id,
                entry_time=datetime.utcnow(),
                status=SessionStatus.ACTIVE, created_by=user_id)
            db.session.add(session)
            db.session.commit()

            cls._active_sessions_cache[plate_norm] = session.id
            AuditService.log("VEHICLE_ENTRY", "ParkingSession", session.id,
                             f"{plate_norm} entered bay {bay.bay_number}, ticket {session.ticket_number}")
            AuditService.log("BAY_ALLOCATED", "ParkingBay", bay.id,
                             f"Bay {bay.bay_number} -> {plate_norm}")
            return {"ok": True, "session": session, "bay": bay}
        except Exception as e:
            db.session.rollback()
            return {"ok": False, "reason": "DB_ERROR", "message": str(e)}

    @classmethod
    def prepare_exit(cls, plate_or_ticket):
        key = (plate_or_ticket or "").strip()
        s = ParkingSession.query.filter_by(ticket_number=key).first()
        if not (s and s.is_active):
            s = cls.get_active_session_by_plate(key)
        if not s:
            return {"ok": False, "reason": "SESSION_NOT_FOUND",
                    "message": "No active session for that plate/ticket."}
        now = datetime.utcnow()
        fee = FeeCalculationService.calculate_fee(s.entry_time, now)
        return {"ok": True, "session": s, "fee": fee, "exit_time": now}

    @classmethod
    def finalise_exit(cls, session_id, user_id=None):
        try:
            s = db.session.get(ParkingSession, session_id)
            if s is None:
                return {"ok": False, "reason": "SESSION_NOT_FOUND"}
            if s.status == SessionStatus.EXITED:
                return {"ok": False, "reason": "ALREADY_EXITED"}
            confirmed = Payment.query.filter_by(
                parking_session_id=s.id, status=PaymentStatus.CONFIRMED).first()
            if not confirmed:
                return {"ok": False, "reason": "PAYMENT_NOT_CONFIRMED"}

            now = datetime.utcnow()
            fee = FeeCalculationService.calculate_fee(s.entry_time, now)
            s.exit_time = now
            s.duration_minutes = fee["duration"]["minutes"]
            s.amount_due = fee["amount"]
            s.status = SessionStatus.EXITED
            s.closed_by = user_id
            if s.bay:
                BayAllocationService.release_bay(s.bay)
            db.session.commit()

            cls._active_sessions_cache.pop(s.vehicle.number_plate, None)
            AuditService.log("VEHICLE_EXIT", "ParkingSession", s.id,
                             f"{s.vehicle.number_plate} exited, KES {s.amount_due}")
            AuditService.log("BAY_RELEASED", "ParkingBay", s.bay.id if s.bay else None,
                             f"Bay released: {s.bay.bay_number if s.bay else 'N/A'}")
            return {"ok": True, "session": s, "payment": confirmed}
        except Exception as e:
            db.session.rollback()
            return {"ok": False, "reason": "DB_ERROR", "message": str(e)}