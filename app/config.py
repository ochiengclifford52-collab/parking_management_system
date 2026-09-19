
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = two levels above this file
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Config:
    """Base settings shared by all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-change-me")

    _default_db_abs = (BASE_DIR / "instance" / "parking.db").resolve()
    _env_url = os.getenv("DATABASE_URL", "").strip()

    if _env_url.startswith("sqlite:///") and not _env_url.startswith("sqlite:////"):

        _relative = _env_url.replace("sqlite:///", "", 1)
        _resolved = (BASE_DIR / _relative).resolve()
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_resolved}"
    elif _env_url:

        SQLALCHEMY_DATABASE_URI = _env_url
    else:

        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_default_db_abs}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------
    PAYMENT_MODE = os.getenv("PAYMENT_MODE", "demo").lower()

    MPESA_ENVIRONMENT = os.getenv("MPESA_ENVIRONMENT", "sandbox")
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")

    # ------------------------------------------------------------
    # Tax
    # ------------------------------------------------------------
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
    """Return the correct config class for the given environment name."""
    mapping = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return mapping.get(name or os.getenv("FLASK_ENV", "development"), DevelopmentConfig)