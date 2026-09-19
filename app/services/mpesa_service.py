"""
M-Pesa Daraja integration with a DEMO simulator.

Modes (env PAYMENT_MODE):
  sandbox  -> real Safaricom Daraja STK Push
  demo     -> no network; the caller drives the state machine via /payments/demo/*

The browser can NEVER declare payment success — only the Daraja callback
(or, in demo mode, the clearly-labelled simulator) moves a payment from
PENDING to CONFIRMED.
"""
import base64
from datetime import datetime
import requests
from flask import current_app
from ..extensions import db
from ..models.payment import Payment, PaymentStatus, PaymentMethod
from .audit_service import AuditService


class MpesaService:

    @classmethod
    def is_demo_mode(cls):
        return current_app.config.get("PAYMENT_MODE", "demo").lower() == "demo"

    @classmethod
    def _base_url(cls):
        env = current_app.config.get("MPESA_ENVIRONMENT", "sandbox").lower()
        return "https://api.safaricom.co.ke" if env == "production" else "https://sandbox.safaricom.co.ke"

    @staticmethod
    def _timestamp():
        return datetime.utcnow().strftime("%Y%m%d%H%M%S")

    @classmethod
    def get_access_token(cls):
        key = current_app.config["MPESA_CONSUMER_KEY"]
        secret = current_app.config["MPESA_CONSUMER_SECRET"]
        if not key or not secret:
            raise RuntimeError("M-Pesa credentials missing. Use DEMO mode or set them in .env.")
        creds = base64.b64encode(f"{key}:{secret}".encode()).decode()
        r = requests.get(f"{cls._base_url()}/oauth/v1/generate?grant_type=client_credentials",
                         headers={"Authorization": f"Basic {creds}"}, timeout=15)
        r.raise_for_status()
        return r.json()["access_token"]

    @staticmethod
    def _normalise_phone(phone):
        if not phone:
            return ""
        p = "".join(ch for ch in phone if ch.isdigit())
        if p.startswith("0") and len(p) == 10:
            return "254" + p[1:]
        if p.startswith("254") and len(p) == 12:
            return p
        if p.startswith("7") and len(p) == 9:
            return "254" + p
        return ""

    @classmethod
    def initiate_stk_push(cls, payment, phone_number):
        phone = cls._normalise_phone(phone_number)
        if not phone:
            return {"ok": False, "reason": "INVALID_PHONE",
                    "message": "Phone must be 2547XXXXXXXX."}

        if cls.is_demo_mode():
            payment.phone_number = phone
            payment.payment_method = PaymentMethod.MPESA
            db.session.commit()
            AuditService.log("MPESA_DEMO_INITIATED", "Payment", payment.id,
                             f"DEMO STK for {phone} KES {payment.amount}")
            return {"ok": True, "mode": "demo", "phone": phone}

        try:
            token = cls.get_access_token()
            ts = cls._timestamp()
            shortcode = current_app.config["MPESA_SHORTCODE"]
            passkey = current_app.config["MPESA_PASSKEY"]
            callback = current_app.config["MPESA_CALLBACK_URL"]
            if not passkey or not callback:
                return {"ok": False, "reason": "MPESA_CONFIG_INCOMPLETE"}
            password = base64.b64encode(f"{shortcode}{passkey}{ts}".encode()).decode()
            payload = {
                "BusinessShortCode": shortcode, "Password": password, "Timestamp": ts,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(round(payment.amount)),
                "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
                "CallBackURL": callback,
                "AccountReference": payment.transaction_reference,
                "TransactionDesc": f"Parking {payment.session.ticket_number}",
            }
            r = requests.post(f"{cls._base_url()}/mpesa/stkpush/v1/processrequest",
                              json=payload,
                              headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"},
                              timeout=20)
            data = r.json()
            if data.get("ResponseCode") == "0":
                payment.merchant_request_id = data.get("MerchantRequestID")
                payment.checkout_request_id = data.get("CheckoutRequestID")
                payment.phone_number = phone
                db.session.commit()
                AuditService.log("MPESA_STK_PUSH_SENT", "Payment", payment.id,
                                 f"STK sent to {phone}, CheckoutID={payment.checkout_request_id}")
                return {"ok": True, "mode": "sandbox",
                        "merchant_request_id": payment.merchant_request_id,
                        "checkout_request_id": payment.checkout_request_id}
            AuditService.log("MPESA_STK_PUSH_FAILED", "Payment", payment.id, str(data))
            return {"ok": False, "reason": "STK_PUSH_FAILED", "raw": data}
        except requests.RequestException as e:
            AuditService.log("MPESA_NETWORK_ERROR", "Payment", payment.id, str(e))
            return {"ok": False, "reason": "NETWORK_ERROR", "message": str(e)}

    @classmethod
    def handle_callback(cls, payload):
        try:
            stk = payload["Body"]["stkCallback"]
            cid = stk.get("CheckoutRequestID")
            code = stk.get("ResultCode")
            desc = stk.get("ResultDesc", "")
        except (KeyError, TypeError):
            return {"ok": False, "reason": "MALFORMED_CALLBACK"}

        payment = Payment.query.filter_by(checkout_request_id=cid).first()
        if payment is None:
            AuditService.log("MPESA_CALLBACK_UNKNOWN", "Payment", None, f"Unknown Cid {cid}")
            return {"ok": False, "reason": "UNKNOWN_CHECKOUT_ID"}
        if payment.status != PaymentStatus.PENDING:
            return {"ok": True, "reason": "DUPLICATE_IGNORED", "status": payment.status}

        from .payment_service import PaymentService
        if code == 0:
            items = stk.get("CallbackMetadata", {}).get("Item", [])
            receipt = next((i["Value"] for i in items if i.get("Name") == "MpesaReceiptNumber"), None)
            return PaymentService.confirm(payment.id, external_reference=receipt)
        return PaymentService.fail(payment.id, reason=desc)