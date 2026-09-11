"""
System health service.

Lightweight, read-only status checks for the dashboard's health panel.
Deliberately simple — this is an operational glance, not a monitoring
system: no external dependencies, no network calls of its own, safe to
compute on every dashboard load.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.models.call import FollowUpCall
from app.models.timeline_event import TimelineEvent
from app.services.demo_scenarios import DEMO_SCENARIOS


@dataclass
class SystemHealth:
    voice_provider: str
    voice_provider_status: str  # "ready" | "not configured"
    notification_service: str
    database_status: str  # "connected" | "error: ..."
    last_webhook_at: Optional[datetime]
    demo_mode_available: bool
    demo_scenario_count: int


def compute_health(config) -> SystemHealth:
    voice_provider = config.get("VOICE_PROVIDER", "mock")
    if voice_provider == "calle":
        voice_provider_status = "ready" if config.get("CALLE_API_KEY") else "not configured (missing CALLE_API_KEY)"
    else:
        voice_provider_status = "ready"

    notification_service = config.get("NOTIFICATION_PROVIDER", "log")

    try:
        FollowUpCall.query.limit(1).all()
        database_status = "connected"
    except Exception as exc:  # noqa: BLE001 - a health check must never itself raise
        database_status = f"error: {exc}"

    last_webhook_event = (
        TimelineEvent.query.filter(
            TimelineEvent.event_type.in_(["call_completed", "call_not_completed"])
        )
        .order_by(TimelineEvent.created_at.desc())
        .first()
    )
    last_webhook_at = last_webhook_event.created_at if last_webhook_event else None

    return SystemHealth(
        voice_provider=voice_provider,
        voice_provider_status=voice_provider_status,
        notification_service=notification_service,
        database_status=database_status,
        last_webhook_at=last_webhook_at,
        demo_mode_available=len(DEMO_SCENARIOS) > 0,
        demo_scenario_count=len(DEMO_SCENARIOS),
    )
