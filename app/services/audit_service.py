"""Audit logging — never breaks the caller on failure."""
from flask import request, has_request_context
from flask_login import current_user
from ..extensions import db
from ..models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def log(action, entity_type=None, entity_id=None, description=None):
        try:
            user_id = None
            if has_request_context() and current_user and getattr(current_user, "is_authenticated", False):
                user_id = current_user.id
            ip = request.headers.get("X-Forwarded-For", request.remote_addr) if has_request_context() else None
            db.session.add(AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                description=description,
                ip_address=ip,
            ))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[AUDIT ERROR] {e}")