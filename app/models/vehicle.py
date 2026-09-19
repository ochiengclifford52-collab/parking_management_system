from datetime import datetime
from ..extensions import db


class Vehicle(db.Model):
    __tablename__ = "vehicles"
    id = db.Column(db.Integer, primary_key=True)
    number_plate = db.Column(db.String(20), unique=True, nullable=False, index=True)
    vehicle_type = db.Column(db.String(30), default="car")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("ParkingSession", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.number_plate}>"