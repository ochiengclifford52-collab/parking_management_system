"""Rate management — add / edit / toggle tariffs."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..models.tariff import Tariff
from ..services.audit_service import AuditService

tariffs_bp = Blueprint("tariffs", __name__)


def _require_admin():
    if not current_user.is_admin:
        abort(403)


@tariffs_bp.route("/")
@login_required
def index():
    _require_admin()
    tariffs = Tariff.query.order_by(Tariff.max_duration_minutes).all()
    return render_template("rates.html", tariffs=tariffs)


@tariffs_bp.route("/add", methods=["POST"])
@login_required
def add():
    _require_admin()
    try:
        name = request.form["name"].strip()
        mx = int(request.form["max_duration_minutes"])
        amt = float(request.form["amount"])
    except (KeyError, ValueError):
        flash("Invalid tariff data.", "danger")
        return redirect(url_for("tariffs.index"))
    t = Tariff(name=name, max_duration_minutes=mx, amount=amt, is_active=True)
    db.session.add(t)
    db.session.commit()
    AuditService.log("RATE_ADDED", "Tariff", t.id, f"{name}: <={mx}min = KES {amt}")
    flash("Tariff added.", "success")
    return redirect(url_for("tariffs.index"))


@tariffs_bp.route("/edit/<int:tariff_id>", methods=["POST"])
@login_required
def edit(tariff_id):
    _require_admin()
    t = Tariff.query.get_or_404(tariff_id)
    old = (t.name, t.max_duration_minutes, t.amount)
    try:
        t.name = request.form.get("name", t.name).strip()
        t.max_duration_minutes = int(request.form.get("max_duration_minutes", t.max_duration_minutes))
        t.amount = float(request.form.get("amount", t.amount))
    except ValueError:
        flash("Invalid values.", "danger")
        return redirect(url_for("tariffs.index"))
    db.session.commit()
    AuditService.log("RATE_CHANGED", "Tariff", t.id,
                     f"{old} -> ({t.name}, {t.max_duration_minutes}, {t.amount})")
    flash("Tariff updated.", "success")
    return redirect(url_for("tariffs.index"))


@tariffs_bp.route("/toggle/<int:tariff_id>", methods=["POST"])
@login_required
def toggle(tariff_id):
    _require_admin()
    t = Tariff.query.get_or_404(tariff_id)
    t.is_active = not t.is_active
    db.session.commit()
    AuditService.log("RATE_TOGGLED", "Tariff", t.id, f"active={t.is_active}")
    flash("Tariff toggled.", "info")
    return redirect(url_for("tariffs.index"))


@tariffs_bp.route("/api")
def api_list():
    tariffs = Tariff.query.filter_by(is_active=True).order_by(Tariff.max_duration_minutes).all()
    return jsonify([{"id": t.id, "name": t.name,
                     "max_duration_minutes": t.max_duration_minutes,
                     "amount": t.amount} for t in tariffs])