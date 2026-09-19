from datetime import datetime
from ..extensions import db


class SessionStatus:
    ACTIVE = "ACTIVE"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    EXITED = "EXITED"
    CANCELLED = "CANCELLED"


class ParkingSession(db.Model):
    __tablename__ = "parking_sessions"
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    bay_id = db.Column(db.Integer, db.ForeignKey("parking_bays.id"), nullable=False)
    entry_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    exit_time = db.Column(db.DateTime, nullable=True, index=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    amount_due = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default=SessionStatus.ACTIVE, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    closed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = db.relationship("Vehicle", back_populates="sessions")
    bay = db.relationship("ParkingBay")
    payments = db.relationship("Payment", back_populates="session", cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.status in (SessionStatus.ACTIVE, SessionStatus.PAYMENT_PENDING, SessionStatus.PAID)