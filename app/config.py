"""
Application configuration.

All configuration is sourced from environment variables (loaded from a local
.env file via python-dotenv in development). Nothing sensitive is hardcoded
here — this file only defines *how* config is read, never the values of
secrets themselves.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///careflow.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Voice provider: "mock" or "calle". Controlled here so the orchestrator
    # can pick the right client without any other module needing to know.
    VOICE_PROVIDER = os.environ.get("VOICE_PROVIDER", "mock")

    CALLE_API_KEY = os.environ.get("CALLE_API_KEY", "")
    # Confirmed against docs.heycall-e.com —
    # the correct domain is api.heycall-e.com, not the earlier best-guess
    # api.call-e.dev used before live documentation was available.
    CALLE_API_BASE_URL = os.environ.get("CALLE_API_BASE_URL", "https://api.heycall-e.com")
    # CALL-E's webhook delivery does not currently use a shared
    # secret (see app/services/calle/calle_client.py::verify_webhook_signature).
    # Kept as a config surface, currently unused, in case CALL-E adds real
    # webhook signing later.
    CALLE_WEBHOOK_SECRET = os.environ.get("CALLE_WEBHOOK_SECRET", "")
    # Optional per-request webhook target. Only needed if you want
    # CALL-E to call back to a specific URL (e.g. an ngrok tunnel during
    # local validation) rather than the account's default webhook endpoint.
    # Leave unset to use the account default.
    CALLE_WEBHOOK_URL = os.environ.get("CALLE_WEBHOOK_URL", "")

    # Only the log notification channel is implemented.
    NOTIFICATION_PROVIDER = os.environ.get("NOTIFICATION_PROVIDER", "log")

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    VOICE_PROVIDER = "mock"


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return CONFIG_MAP.get(env, DevelopmentConfig)
