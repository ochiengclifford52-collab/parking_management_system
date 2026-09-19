"""Payments: checkout, status, receipt, M-Pesa callback, demo, barrier, finalise."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ..extensions import db, csrf
from ..models.parking_session import ParkingSession
from ..models.payment import Payment, PaymentMethod, PaymentStatus
from ..services.parking_service import ParkingService
from ..services.payment_service import PaymentService
from ..services.mpesa_service import MpesaService
from ..services.barrier_service import BarrierService

payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/checkout/<int:session_id>", methods=["GET", "POST"])
@login_required
def checkout(session_id):
    session = ParkingSession.query.get_or_404(session_id)

    if request.method == "POST":
        method = request.form.get("method", "").upper()
        if method not in PaymentMethod.ALL:
            flash("Invalid payment method.", "danger")
            return redirect(url_for("payments.checkout", session_id=session_id))

        r = ParkingService.prepare_exit(session.ticket_number)
        if not r["ok"]:
            flash(r["message"], "danger")
            return redirect(url_for("payments.checkout", session_id=session_id))
        amount = r["fee"]["amount"]

        if method == PaymentMethod.CASH:
            try:
                cash = float(request.form.get("cash_received", "0"))
            except ValueError:
                cash = 0.0
            res = PaymentService.process_cash(session, amount, cash, current_user.id)
            if not res["ok"]:
                flash(res.get("message", res["reason"]), "danger")
                return redirect(url_for("payments.checkout", session_id=session_id))
            return redirect(url_for("payments.status", payment_id=res["payment"].id))

        if method == PaymentMethod.MPESA:
            phone = request.form.get("phone_number", "").strip()
            p = PaymentService.create_pending(session, amount, PaymentMethod.MPESA, phone=phone)
            stk = MpesaService.initiate_stk_push(p, phone)
            if not stk["ok"]:
                PaymentService.fail(p.id, reason=stk.get("reason", "STK_FAILED"))
                flash(stk.get("message", "M-Pesa request failed."), "danger")
                return redirect(url_for("payments.checkout", session_id=session_id))
            return redirect(url_for("payments.status", payment_id=p.id))

        if method == PaymentMethod.CARD:
            last4 = request.form.get("card_last4", "4242")
            p = PaymentService.create_pending(session, amount, PaymentMethod.CARD)
            p.external_reference = f"SIMCARD-****{last4}"
            db.session.commit()
            PaymentService.confirm(p.id)
            return redirect(url_for("payments.status", payment_id=p.id))

    r = ParkingService.prepare_exit(session.ticket_number)
    return render_template("payment.html", session=session,
                           fee=r["fee"] if r["ok"] else None,
                           payment_mode="demo" if MpesaService.is_demo_mode() else "sandbox")


@payments_bp.route("/status/<int:payment_id>")
@login_required
def status(payment_id):
    p = Payment.query.get_or_404(payment_id)
    return render_template("payment_status.html", payment=p, session=p.session)


@payments_bp.route("/receipt/<int:payment_id>")
@login_required
def receipt(payment_id):
    p = Payment.query.get_or_404(payment_id)
    if p.status != PaymentStatus.CONFIRMED:
        flash("Receipt only for confirmed payments.", "warning")
        return redirect(url_for("payments.status", payment_id=payment_id))
    return render_template("receipt.html", payment=p, session=p.session)


@payments_bp.route("/list")
@login_required
def list_payments():
    q = Payment.query
    if request.args.get("status"):
        q = q.filter(Payment.status == request.args["status"])
    if request.args.get("method"):
        q = q.filter(Payment.payment_method == request.args["method"])
    if request.args.get("ref"):
        like = f"%{request.args['ref']}%"
        q = q.join(ParkingSession).filter(db.or_(
            Payment.transaction_reference.ilike(like),
            Payment.external_reference.ilike(like),
            ParkingSession.ticket_number.ilike(like)))
    payments = q.order_by(Payment.created_at.desc()).limit(200).all()
    return render_template("payments_list.html", payments=payments,
                           statuses=PaymentStatus.ALL, methods=PaymentMethod.ALL)


@payments_bp.route("/mpesa/callback", methods=["POST"])
@csrf.exempt
def mpesa_callback():
    payload = request.get_json(silent=True) or {}
    result = MpesaService.handle_callback(payload)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted", "internal": result}), 200


@payments_bp.route("/demo/confirm/<int:payment_id>", methods=["POST"])
@login_required
def demo_confirm(payment_id):
    if not MpesaService.is_demo_mode():
        return jsonify({"ok": False, "error": "Demo disabled in sandbox mode."}), 400
    r = PaymentService.confirm(payment_id, external_reference=f"DEMO-{payment_id:06d}")
    if not r["ok"]:
        return jsonify(r), 400
    return redirect(url_for("payments.status", payment_id=payment_id))


@payments_bp.route("/demo/fail/<int:payment_id>", methods=["POST"])
@login_required
def demo_fail(payment_id):
    if not MpesaService.is_demo_mode():
        return jsonify({"ok": False, "error": "Demo disabled."}), 400
    r = PaymentService.fail(payment_id, reason="DEMO_FAILURE")
    if not r["ok"]:
        return jsonify(r), 400
    return redirect(url_for("payments.status", payment_id=payment_id))


@payments_bp.route("/barrier/open/<int:session_id>", methods=["POST"])
@login_required
def barrier_open(session_id):
    r = BarrierService.open_barrier(session_id)
    if not r["ok"]:
        flash(f"Barrier refused: {r['reason']}", "danger")
    else:
        flash("Barrier opened. Vehicle may exit.", "success")
    payment = Payment.query.filter_by(parking_session_id=session_id,
                                      status=PaymentStatus.CONFIRMED).first()
    if payment:
        return redirect(url_for("payments.status", payment_id=payment.id))
    return redirect(url_for("dashboard.index"))


@payments_bp.route("/finalise/<int:session_id>", methods=["POST"])
@login_required
def finalise(session_id):
    r = ParkingService.finalise_exit(session_id, user_id=current_user.id)
    if not r["ok"]:
        flash(f"Could not finalise: {r['reason']}", "danger")
        return redirect(url_for("dashboard.index"))
    flash("Vehicle exited. Bay released.", "success")
    return redirect(url_for("payments.receipt", payment_id=r["payment"].id))