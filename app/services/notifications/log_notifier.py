"""Log notification requests without external delivery.

This is the only implemented notification channel. A successful result
means the request was logged, not that a person received a message.
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
