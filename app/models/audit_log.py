from datetime import datetime
from ..extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(60), nullable=False, index=True)
    entity_type = db.Column(db.String(40), nullable=True)
    entity_id = db.Column(db.String(40), nullable=True)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User")