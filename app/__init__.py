"""Flask application factory."""
import os
from flask import Flask, render_template
from .config import get_config
from .extensions import db, login_manager, csrf


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.parking import parking_bp
    from .routes.payments import payments_bp
    from .routes.reports import reports_bp
    from .routes.tariffs import tariffs_bp
    from .routes.admin import admin_bp
    from .routes.public import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(parking_bp, url_prefix="/parking")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(tariffs_bp, url_prefix="/tariffs")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(public_bp)

    with app.app_context():
        from . import models  # noqa: F401  (registers all models)
        db.create_all()

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app