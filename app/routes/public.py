"""Public driver view."""
from flask import Blueprint, render_template, jsonify
from ..models.parking_bay import ParkingBay, BayStatus

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    bays = ParkingBay.query.order_by(ParkingBay.bay_number).all()
    counts = {"total": len(bays),
              "available": sum(1 for b in bays if b.status == BayStatus.AVAILABLE),
              "occupied": sum(1 for b in bays if b.status == BayStatus.OCCUPIED),
              "out_of_service": sum(1 for b in bays if b.status == BayStatus.OUT_OF_SERVICE)}
    return render_template("public_availability.html", bays=bays, counts=counts)


@public_bp.route("/api/availability")
def api_availability():
    bays = ParkingBay.query.order_by(ParkingBay.bay_number).all()
    return jsonify({
        "bays": [{"bay_number": b.bay_number, "status": b.status} for b in bays],
        "counts": {"total": len(bays),
                   "available": sum(1 for b in bays if b.status == BayStatus.AVAILABLE),
                   "occupied": sum(1 for b in bays if b.status == BayStatus.OCCUPIED),
                   "out_of_service": sum(1 for b in bays if b.status == BayStatus.OUT_OF_SERVICE)}})