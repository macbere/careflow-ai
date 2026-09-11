"""
Log-based notification channel.

Phase 2's default (and only) concrete implementation. Logs the notification
clearly instead of sending a real email/SMS/Slack message — this keeps the
escalation *workflow* fully built and demoable while the real delivery
channel is deferred, per the approved phased scope. Swapping this for a
real channel later (e.g. `SmtpNotificationService`) requires no changes
outside this file and the factory in `__init__.py`.
"""
from app.extensions import logger
from app.services.notifications.base import (
    NotificationRequest,
    NotificationResult,
    NotificationService,
)


class LogNotificationService(NotificationService):
    def send(self, request: NotificationRequest) -> NotificationResult:
        logger.warning(
            "[NOTIFICATION:%s] %s — %s (metadata=%s)",
            request.recipient_hint,
            request.subject,
            request.message,
            request.metadata,
        )
        return NotificationResult(
            success=True,
            channel="log",
            detail="Logged notification (stub channel — no real delivery in Phase 2)",
        )
