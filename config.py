import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key")
    # SQLite default — the instance/ folder keeps the DB out of git
    _db_path = BASE_DIR / "instance" / "parking.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{_db_path}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PAYMENT_MODE = os.getenv("PAYMENT_MODE", "demo").lower()

    MPESA_ENVIRONMENT = os.getenv("MPESA_ENVIRONMENT", "sandbox")
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")

    VAT_RATE = float(os.getenv("VAT_RATE", "16"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    PAYMENT_MODE = "demo"


class ProductionConfig(Config):
    DEBUG = False


def get_config(name=None):
    mapping = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return mapping.get(name or os.getenv("FLASK_ENV", "development"), DevelopmentConfig)