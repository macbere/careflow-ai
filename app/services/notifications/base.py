"""Notification requests, results, and the channel interface.

The escalation service uses this interface; channel implementations are
selected in get_notification_service().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class NotificationRequest:
    """Everything a notification channel needs to send an alert."""

    subject: str
    message: str
    # Informational role label; the log channel does not route to a person.
    recipient_hint: str = "on_call_nurse"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationResult:
    success: bool
    channel: str
    detail: Optional[str] = None


class NotificationService(ABC):
    """Abstract base class every notification channel must implement."""

    @abstractmethod
    def send(self, request: NotificationRequest) -> NotificationResult:
        raise NotImplementedError
