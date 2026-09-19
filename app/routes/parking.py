"""Parking operations: map, entry, exit, AJAX availability."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ..services.parking_service import ParkingService
from ..models.parking_bay import ParkingBay, BayStatus
from ..models.parking_session import ParkingSession

parking_bp = Blueprint("parking", __name__)


@parking_bp.route("/")
@login_required
def index():
    bays = ParkingBay.query.order_by(ParkingBay.bay_number).all()
    counts = {"total": len(bays),
              "available": sum(1 for b in bays if b.status == BayStatus.AVAILABLE),
              "occupied": sum(1 for b in bays if b.status == BayStatus.OCCUPIED),
              "out_of_service": sum(1 for b in bays if b.status == BayStatus.OUT_OF_SERVICE)}
    return render_template("parking_map.html", bays=bays, counts=counts)


@parking_bp.route("/entry", methods=["GET", "POST"])
@login_required
def entry():
    if request.method == "POST":
        plate = request.form.get("number_plate", "").strip().upper()
        vtype = request.form.get("vehicle_type", "car")
        r = ParkingService.register_entry(plate, user_id=current_user.id, vehicle_type=vtype)
        if r["ok"]:
            flash(f"Vehicle {plate} → Bay {r['bay'].bay_number} | Ticket {r['session'].ticket_number}", "success")
            return redirect(url_for("parking.session_view", session_id=r["session"].id))
        flash(r.get("message", r["reason"]), "danger")
    return render_template("vehicle_entry.html")


@parking_bp.route("/session/<int:session_id>")
@login_required
def session_view(session_id):
    s = ParkingSession.query.get_or_404(session_id)
    return render_template("session_detail.html", session=s)


@parking_bp.route("/exit", methods=["GET", "POST"])
@login_required
def exit_view():
    if request.method == "POST":
        key = request.form.get("plate_or_ticket", "").strip()
        r = ParkingService.prepare_exit(key)
        if not r["ok"]:
            flash(r["message"], "danger")
            return render_template("vehicle_exit.html")
        return render_template("vehicle_exit.html", session=r["session"],
                               fee=r["fee"], exit_time=r["exit_time"])
    return render_template("vehicle_exit.html")


@parking_bp.route("/api/availability")
def api_availability():
    bays = ParkingBay.query.order_by(ParkingBay.bay_number).all()
    return jsonify({
        "bays": [{"bay_number": b.bay_number, "status": b.status} for b in bays],
        "counts": {"total": len(bays),
                   "available": sum(1 for b in bays if b.status == BayStatus.AVAILABLE),
                   "occupied": sum(1 for b in bays if b.status == BayStatus.OCCUPIED),
                   "out_of_service": sum(1 for b in bays if b.status == BayStatus.OUT_OF_SERVICE)}})