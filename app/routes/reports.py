"""Reports and CSV export."""
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, Response, abort
from flask_login import login_required, current_user
from ..models.payment import Payment, PaymentStatus
from ..models.audit_log import AuditLog
from ..services.report_service import ReportService

reports_bp = Blueprint("reports", __name__)


def _require_manager():
    if not current_user.has_role("admin", "auditor"):
        abort(403)


@reports_bp.route("/")
@login_required
def index():
    _require_manager()
    today = datetime.utcnow().date()
    sod = datetime.combine(today, datetime.min.time())
    data = {
        "daily": ReportService.revenue_between(sod, sod + timedelta(days=1)),
        "weekly": ReportService.revenue_between(sod - timedelta(days=6), sod + timedelta(days=1)),
        "monthly": ReportService.revenue_between(sod - timedelta(days=29), sod + timedelta(days=1)),
        "methods": ReportService.payment_method_breakdown(sod - timedelta(days=29)),
        "vat": ReportService.vat_summary(sod - timedelta(days=29)),
        "daily_series": ReportService.daily_revenue(30),
        "utilization": ReportService.bay_utilization(),
        "failed": ReportService.failed_payments(20),
    }
    return render_template("reports.html", data=data)


@reports_bp.route("/revenue.csv")
@login_required
def revenue_csv():
    _require_manager()
    rows = Payment.query.filter(Payment.status == PaymentStatus.CONFIRMED)\
                        .order_by(Payment.confirmed_at).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Reference", "Ticket", "Plate", "Method",
                "Gross", "VAT", "Net", "External Ref"])
    for p in rows:
        w.writerow([
            p.confirmed_at.isoformat() if p.confirmed_at else "",
            p.transaction_reference,
            p.session.ticket_number if p.session else "",
            p.session.vehicle.number_plate if p.session and p.session.vehicle else "",
            p.payment_method,
            f"{p.amount:.2f}", f"{(p.vat_amount or 0):.2f}", f"{(p.net_amount or 0):.2f}",
            p.external_reference or ""])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=revenue.csv"})


@reports_bp.route("/audit-logs")
@login_required
def audit_logs():
    _require_manager()
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(500).all()
    return render_template("audit_logs.html", logs=logs)