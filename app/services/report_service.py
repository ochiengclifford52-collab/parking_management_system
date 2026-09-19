"""Reporting and dashboard aggregations."""
from datetime import datetime, timedelta
from sqlalchemy import func
from ..extensions import db
from ..models.parking_session import ParkingSession
from ..models.parking_bay import ParkingBay, BayStatus
from ..models.payment import Payment, PaymentStatus


class ReportService:

    @staticmethod
    def dashboard_stats():
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        today_end = today_start + timedelta(days=1)
        return {
            "total_bays": ParkingBay.query.count(),
            "available": ParkingBay.query.filter_by(status=BayStatus.AVAILABLE).count(),
            "occupied": ParkingBay.query.filter_by(status=BayStatus.OCCUPIED).count(),
            "out_of_service": ParkingBay.query.filter_by(status=BayStatus.OUT_OF_SERVICE).count(),
            "vehicles_parked": ParkingBay.query.filter_by(status=BayStatus.OCCUPIED).count(),
            "today_entries": ParkingSession.query.filter(
                ParkingSession.entry_time >= today_start,
                ParkingSession.entry_time < today_end).count(),
            "today_exits": ParkingSession.query.filter(
                ParkingSession.exit_time >= today_start,
                ParkingSession.exit_time < today_end).count(),
            "today_revenue": float(db.session.query(
                func.coalesce(func.sum(Payment.amount), 0.0)).filter(
                Payment.status == PaymentStatus.CONFIRMED,
                Payment.confirmed_at >= today_start,
                Payment.confirmed_at < today_end).scalar() or 0.0),
        }

    @staticmethod
    def revenue_between(start, end):
        return float(db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))
                     .filter(Payment.status == PaymentStatus.CONFIRMED,
                             Payment.confirmed_at >= start,
                             Payment.confirmed_at < end).scalar() or 0.0)

    @staticmethod
    def daily_revenue(days=14):
        """
        Return [(date_str, total_float), ...] for the last `days` days.
        Missing days are returned with a total of 0.0.
        """
        end = datetime.utcnow()
        start = (end - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Run the aggregate query.
        # We intentionally tuple-unpack the row (d, total) instead of
        # accessing attributes like r.d / r.t — the unpacked form is
        # unambiguous across SQLAlchemy versions.
        rows = (
            db.session.query(
                func.date(Payment.confirmed_at).label("d"),
                func.sum(Payment.amount).label("total"),
            )
            .filter(
                Payment.status == PaymentStatus.CONFIRMED,
                Payment.confirmed_at >= start,
            )
            .group_by("d")
            .order_by("d")
            .all()
        )

        # Build a lookup: date string -> float total
        mapping = {}
        for d, total in rows:
            mapping[str(d)] = float(total or 0.0)

        # Fill in every day in the window, including days with no payments.
        result = []
        for i in range(days):
            d = str((start + timedelta(days=i)).date())
            result.append((d, mapping.get(d, 0.0)))
        return result

    @staticmethod
    def payment_method_breakdown(start=None, end=None):
        q = (db.session.query(Payment.payment_method,
                              func.sum(Payment.amount).label("total"),
                              func.count(Payment.id).label("cnt"))
             .filter(Payment.status == PaymentStatus.CONFIRMED))
        if start:
            q = q.filter(Payment.confirmed_at >= start)
        if end:
            q = q.filter(Payment.confirmed_at < end)
        return q.group_by(Payment.payment_method).all()

    @staticmethod
    def failed_payments(limit=100):
        return (Payment.query.filter_by(status=PaymentStatus.FAILED)
                .order_by(Payment.created_at.desc()).limit(limit).all())

    @staticmethod
    def vat_summary(start=None, end=None):
        q = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0.0).label("gross"),
            func.coalesce(func.sum(Payment.vat_amount), 0.0).label("vat"),
            func.coalesce(func.sum(Payment.net_amount), 0.0).label("net"),
        ).filter(Payment.status == PaymentStatus.CONFIRMED)
        if start:
            q = q.filter(Payment.confirmed_at >= start)
        if end:
            q = q.filter(Payment.confirmed_at < end)
        row = q.one()
        return {"gross": float(row.gross), "vat": float(row.vat), "net": float(row.net)}

    @staticmethod
    def bay_utilization():
        rows = (db.session.query(ParkingBay.bay_number,
                                 func.count(ParkingSession.id).label("uses"))
                .outerjoin(ParkingSession, ParkingSession.bay_id == ParkingBay.id)
                .group_by(ParkingBay.id).order_by(ParkingBay.bay_number).all())
        return [{"bay": r.bay_number, "uses": r.uses} for r in rows]