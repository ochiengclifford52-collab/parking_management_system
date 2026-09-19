"""Login / logout."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models.user import User
from ..services.audit_service import AuditService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            AuditService.log("USER_LOGIN", "User", user.id, f"{user.username} logged in")
            return redirect(request.args.get("next") or url_for("dashboard.index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    AuditService.log("USER_LOGOUT", "User", current_user.id, f"{current_user.username} logged out")
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))