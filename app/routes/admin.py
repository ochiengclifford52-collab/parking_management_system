"""Admin: bays, users, settings."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..models.parking_bay import ParkingBay, BayStatus
from ..models.user import User, Role
from ..models.setting import SystemSetting
from ..services.audit_service import AuditService

admin_bp = Blueprint("admin", __name__)


def _require_admin():
    if not current_user.is_admin:
        abort(403)


@admin_bp.route("/")
@login_required
def index():
    _require_admin()
    return render_template("admin.html",
                           bays=ParkingBay.query.order_by(ParkingBay.bay_number).all(),
                           users=User.query.order_by(User.username).all(),
                           settings=SystemSetting.query.all())


@admin_bp.route("/bays/add", methods=["POST"])
@login_required
def add_bay():
    _require_admin()
    number = request.form.get("bay_number", "").strip().upper()
    zone = request.form.get("zone", "A").strip().upper() or "A"
    if not number:
        flash("Bay number required.", "danger")
        return redirect(url_for("admin.index"))
    if ParkingBay.query.filter_by(bay_number=number).first():
        flash(f"Bay {number} exists.", "warning")
        return redirect(url_for("admin.index"))
    bay = ParkingBay(bay_number=number, zone=zone, status=BayStatus.AVAILABLE)
    db.session.add(bay)
    db.session.commit()
    AuditService.log("BAY_ADDED", "ParkingBay", bay.id, f"{number} zone {zone}")
    flash("Bay added.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/bays/<int:bay_id>/status", methods=["POST"])
@login_required
def set_bay_status(bay_id):
    _require_admin()
    bay = ParkingBay.query.get_or_404(bay_id)
    new_status = request.form.get("status", "").upper()
    if new_status not in BayStatus.ALL:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin.index"))
    if bay.status == BayStatus.OCCUPIED and new_status != BayStatus.OCCUPIED:
        flash("Cannot free an occupied bay manually.", "warning")
        return redirect(url_for("admin.index"))
    old = bay.status
    bay.status = new_status
    db.session.commit()
    AuditService.log("BAY_STATUS_CHANGED", "ParkingBay", bay.id, f"{old} → {new_status}")
    flash("Bay status updated.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/add", methods=["POST"])
@login_required
def add_user():
    _require_admin()
    username = request.form.get("username", "").strip().lower()
    full_name = request.form.get("full_name", "").strip()
    password = request.form.get("password", "")
    role_name = request.form.get("role", "attendant").strip().lower()
    if not (username and password and full_name):
        flash("All fields required.", "danger")
        return redirect(url_for("admin.index"))
    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "warning")
        return redirect(url_for("admin.index"))
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash("Unknown role.", "danger")
        return redirect(url_for("admin.index"))
    u = User(username=username, full_name=full_name, role_id=role.id)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    AuditService.log("USER_CREATED", "User", u.id, f"{username} ({role_name})")
    flash("User created.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_user(user_id):
    _require_admin()
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash("Cannot deactivate yourself.", "warning")
        return redirect(url_for("admin.index"))
    u.is_active = not u.is_active
    db.session.commit()
    AuditService.log("USER_TOGGLED", "User", u.id, f"active={u.is_active}")
    flash("User toggled.", "info")
    return redirect(url_for("admin.index"))


@admin_bp.route("/settings", methods=["POST"])
@login_required
def save_settings():
    _require_admin()
    for key in ("vat_rate", "site_name"):
        if key in request.form:
            SystemSetting.set(key, request.form[key], description=key)
            AuditService.log("SETTING_CHANGED", "SystemSetting", None, f"{key}={request.form[key]}")
    flash("Settings saved.", "success")
    return redirect(url_for("admin.index"))