"""
Factory for selecting the active notification channel based on config.

Mirrors app/services/calle/__init__.py's get_voice_client() pattern for
consistency. Only "log" exists in Phase 2; the branch structure is here so
adding NOTIFICATION_PROVIDER=smtp/slack/sms later is a small, obvious diff.
"""
from app.services.notifications.base import NotificationService
from app.services.notifications.log_notifier import LogNotificationService


def get_notification_service(config=None) -> NotificationService:
    """
    `config` is Flask's `app.config` (dict-like) or None. Accepting None
    keeps this callable from plain Python/tests without an app context.
    """
    provider = (config or {}).get("NOTIFICATION_PROVIDER", "log") if config else "log"

    # Future: elif provider == "smtp": return SmtpNotificationService(...)
    # Future: elif provider == "slack": return SlackNotificationService(...)
    return LogNotificationService()
