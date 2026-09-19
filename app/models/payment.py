from datetime import datetime
from ..extensions import db


class PaymentStatus:
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    ALL = (PENDING, CONFIRMED, FAILED, CANCELLED, REFUNDED)


class PaymentMethod:
    MPESA = "MPESA"
    CARD = "CARD"
    CASH = "CASH"
    ALL = (MPESA, CARD, CASH)


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    parking_session_id = db.Column(db.Integer, db.ForeignKey("parking_sessions.id"), nullable=False)
    transaction_reference = db.Column(db.String(60), unique=True, nullable=False, index=True)
    external_reference = db.Column(db.String(80), nullable=True)
    payment_method = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default=PaymentStatus.PENDING, index=True)
    phone_number = db.Column(db.String(20), nullable=True)
    merchant_request_id = db.Column(db.String(80), nullable=True)
    checkout_request_id = db.Column(db.String(80), nullable=True, index=True)
    cash_received = db.Column(db.Float, nullable=True)
    change_given = db.Column(db.Float, nullable=True)
    vat_amount = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, default=0.0)
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = db.relationship("ParkingSession", back_populates="payments")