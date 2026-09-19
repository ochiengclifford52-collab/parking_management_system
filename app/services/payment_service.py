"""
Payment state machine.

    PENDING --> CONFIRMED --> REFUNDED
       |
       +--> FAILED
       +--> CANCELLED

Transitions are enforced here. Only CONFIRMED payments authorise exit.
"""
import uuid
from datetime import datetime
from flask import current_app
from ..extensions import db
from ..models.payment import Payment, PaymentStatus, PaymentMethod
from ..models.parking_session import SessionStatus
from ..models.setting import SystemSetting
from .audit_service import AuditService


class PaymentService:

    @staticmethod
    def get_vat_rate():
        v = SystemSetting.get("vat_rate")
        try:
            return float(v) if v is not None else float(current_app.config.get("VAT_RATE", 16.0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _split_vat(gross):
        rate = PaymentService.get_vat_rate()
        if rate <= 0:
            return gross, 0.0
        net = round(gross / (1 + rate / 100.0), 2)
        return net, round(gross - net, 2)

    @staticmethod
    def generate_reference():
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"

    @classmethod
    def create_pending(cls, session, amount, method, phone=None):
        net, vat = cls._split_vat(amount)
        p = Payment(parking_session_id=session.id,
                    transaction_reference=cls.generate_reference(),
                    payment_method=method, amount=amount,
                    net_amount=net, vat_amount=vat,
                    status=PaymentStatus.PENDING, phone_number=phone)
        db.session.add(p)
        session.status = SessionStatus.PAYMENT_PENDING
        session.amount_due = amount
        db.session.commit()
        AuditService.log("PAYMENT_INITIATED", "Payment", p.id,
                         f"{method} KES {amount} for {session.ticket_number}")
        return p

    @classmethod
    def confirm(cls, payment_id, external_reference=None):
        p = db.session.get(Payment, payment_id)
        if p is None:
            return {"ok": False, "reason": "PAYMENT_NOT_FOUND"}
        if p.status == PaymentStatus.CONFIRMED:
            return {"ok": True, "payment": p, "already_confirmed": True}
        if p.status != PaymentStatus.PENDING:
            return {"ok": False, "reason": f"INVALID_TRANSITION_FROM_{p.status}"}
        p.status = PaymentStatus.CONFIRMED
        p.confirmed_at = datetime.utcnow()
        if external_reference:
            p.external_reference = external_reference
        if p.session:
            p.session.status = SessionStatus.PAID
        db.session.commit()
        AuditService.log("PAYMENT_CONFIRMED", "Payment", p.id,
                         f"{p.payment_method} KES {p.amount} ref {external_reference or p.transaction_reference}")
        return {"ok": True, "payment": p}

    @classmethod
    def fail(cls, payment_id, reason=""):
        p = db.session.get(Payment, payment_id)
        if p is None:
            return {"ok": False, "reason": "PAYMENT_NOT_FOUND"}
        if p.status != PaymentStatus.PENDING:
            return {"ok": False, "reason": f"INVALID_TRANSITION_FROM_{p.status}"}
        p.status = PaymentStatus.FAILED
        if p.session:
            p.session.status = SessionStatus.ACTIVE
        db.session.commit()
        AuditService.log("PAYMENT_FAILED", "Payment", p.id, reason)
        return {"ok": True, "payment": p}

    @classmethod
    def process_cash(cls, session, amount_due, cash_received, user_id=None):
        if cash_received < amount_due:
            return {"ok": False, "reason": "INSUFFICIENT_CASH",
                    "message": f"Cash KES {cash_received} < KES {amount_due} due."}
        p = cls.create_pending(session, amount_due, PaymentMethod.CASH)
        p.cash_received = cash_received
        p.change_given = round(cash_received - amount_due, 2)
        db.session.commit()
        return cls.confirm(p.id)