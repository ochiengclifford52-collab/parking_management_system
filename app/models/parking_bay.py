from datetime import datetime
from ..extensions import db


class BayStatus:
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    ALL = (AVAILABLE, OCCUPIED, OUT_OF_SERVICE)


class ParkingBay(db.Model):
    __tablename__ = "parking_bays"
    id = db.Column(db.Integer, primary_key=True)
    bay_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    zone = db.Column(db.String(10), default="A")
    status = db.Column(db.String(20), default=BayStatus.AVAILABLE, index=True)
    is_priority = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Bay {self.bay_number} {self.status}>"