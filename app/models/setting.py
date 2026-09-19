from datetime import datetime
from ..extensions import db


class SystemSetting(db.Model):
    __tablename__ = "system_settings"
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(60), unique=True, nullable=False)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get(key, default=None):
        row = SystemSetting.query.filter_by(setting_key=key).first()
        return row.setting_value if row else default

    @staticmethod
    def set(key, value, description=None):
        row = SystemSetting.query.filter_by(setting_key=key).first()
        if row:
            row.setting_value = str(value)
        else:
            db.session.add(SystemSetting(setting_key=key, setting_value=str(value), description=description))
        db.session.commit()