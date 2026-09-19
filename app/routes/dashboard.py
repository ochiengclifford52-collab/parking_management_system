"""Dashboard."""
from flask import Blueprint, render_template
from flask_login import login_required
from ..models.parking_bay import ParkingBay
from ..services.report_service import ReportService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    stats = ReportService.dashboard_stats()
    bays = ParkingBay.query.order_by(ParkingBay.bay_number).all()
    chart = ReportService.daily_revenue(days=7)
    return render_template("dashboard.html", stats=stats, bays=bays,
                           chart_labels=[c[0] for c in chart],
                           chart_values=[c[1] for c in chart])