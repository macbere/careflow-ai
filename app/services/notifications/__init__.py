"""Return the notification service. Only the log channel is implemented."""
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
