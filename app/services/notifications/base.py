"""
Abstract notification service interface.

The escalation workflow (app/services/escalation_service.py) depends only
on this interface, never on a concrete channel. Adding SMTP, Slack, or SMS
later means writing one new class here and registering it in
`get_notification_service()` (app/services/notifications/__init__.py) —
nothing in escalation_service.py or call_orchestrator.py changes. This
mirrors the same abstraction pattern used for the CALL-E voice provider in
app/services/calle/base.py.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class NotificationRequest:
    """Everything a notification channel needs to send an alert."""

    subject: str
    message: str
    # Free-form recipient hint (e.g. a role like "on_call_nurse") — Phase 2
    # doesn't route to real people/channels yet, so this is informational.
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
