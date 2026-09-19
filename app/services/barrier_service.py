"""
Software barrier simulation with a SAFETY GUARD.

open_barrier() re-reads the DB and refuses unless a CONFIRMED
payment exists for the session. This makes it impossible for a
buggy caller (or a malicious browser) to open the barrier before
payment is verified.
"""
import threading
from datetime import datetime
from ..models.parking_session import ParkingSession
from ..models.payment import Payment, PaymentStatus
from .audit_service import AuditService


class BarrierState:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    CLOSING = "CLOSING"
    ERROR = "ERROR"


class BarrierService:
    _lock = threading.Lock()
    _state = BarrierState.CLOSED
    _last_event_at = None

    @classmethod
    def get_status(cls):
        return {"state": cls._state, "last_event_at": cls._last_event_at}

    @classmethod
    def open_barrier(cls, session_id):
        with cls._lock:
            session = ParkingSession.query.get(session_id)
            if session is None:
                return {"ok": False, "reason": "SESSION_NOT_FOUND"}
            confirmed = Payment.query.filter_by(
                parking_session_id=session.id, status=PaymentStatus.CONFIRMED).first()
            if not confirmed:
                AuditService.log("BARRIER_OPEN_REFUSED", "ParkingSession", session.id,
                                 "Barrier refused: no confirmed payment")
                return {"ok": False, "reason": "PAYMENT_NOT_CONFIRMED"}
            cls._state = BarrierState.OPENING
            cls._state = BarrierState.OPEN
            cls._last_event_at = datetime.utcnow()
            AuditService.log("BARRIER_OPENED", "ParkingSession", session.id,
                             f"Barrier opened for {session.ticket_number}")
            return {"ok": True, "state": cls._state}

    @classmethod
    def close_barrier(cls):
        with cls._lock:
            cls._state = BarrierState.CLOSING
            cls._state = BarrierState.CLOSED
            cls._last_event_at = datetime.utcnow()
            AuditService.log("BARRIER_CLOSED", "Barrier", None, "Barrier closed")
            return {"ok": True, "state": cls._state}