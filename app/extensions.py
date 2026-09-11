"""
Shared extension instances.

Kept in their own module (rather than instantiated inside __init__.py) so
that model files and service files can import `db` without triggering a
circular import with the application factory.
"""
import logging
import sys
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow() -> datetime:
    """
    Naive UTC datetime — same value and comparability as the old
    `datetime.utcnow()` (still naive, so it stores/compares identically
    against existing SQLite-backed columns), but built via
    `datetime.now(timezone.utc)` so it doesn't trigger the deprecation
    warning Python 3.12+ raises on calling `datetime.utcnow()` directly.
    Use this everywhere in the app instead of `datetime.utcnow()`.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def configure_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure a single shared logger for the application.

    Logs to stdout so they're captured by whatever process manager runs the
    app (local terminal, Render logs, etc.) without needing extra file
    handling for the hackathon deployment.
    """
    logger = logging.getLogger("careflow")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = configure_logging()
