from datetime import datetime
from ..extensions import db


class Tariff(db.Model):
    __tablename__ = "tariffs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    max_duration_minutes = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    effective_from = db.Column(db.DateTime, default=datetime.utcnow)
    effective_to = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tariff {self.name} ≤{self.max_duration_minutes}min=KES{self.amount}>"