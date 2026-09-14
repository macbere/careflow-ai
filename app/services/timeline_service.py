"""Write and retrieve timeline events for patients, discharges, and calls."""
from typing import Any, Dict, Optional

from app.extensions import db, logger
from app.models.timeline_event import TimelineEvent


def log_event(
    event_type: str,
    title: str,
    description: str = "",
    patient_id: Optional[int] = None,
    discharge_id: Optional[int] = None,
    call_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    commit: bool = True,
) -> TimelineEvent:
    """
    Record a timeline event.

    `commit` defaults to True for simple, single-step call sites (e.g. patient
    creation). Multi-step flows in call_orchestrator.py pass commit=False and
    rely on the orchestrator's own commit() at the end of the step, so a
    timeline write never partially persists ahead of the state it describes.
    """
    event = TimelineEvent(
        event_type=event_type,
        title=title,
        description=description,
        patient_id=patient_id,
        discharge_id=discharge_id,
        call_id=call_id,
        event_metadata=metadata or {},
    )
    db.session.add(event)

    if commit:
        db.session.commit()
    else:
        db.session.flush()

    logger.info("Timeline event logged: %s — %s", event_type, title)
    return event


def log_event_once(
    event_type: str,
    title: str,
    description: str = "",
    patient_id: Optional[int] = None,
    discharge_id: Optional[int] = None,
    call_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    commit: bool = True,
) -> TimelineEvent:
    """Return the existing call-scoped event or create it exactly once."""
    if call_id is None:
        return log_event(
            event_type,
            title,
            description,
            patient_id,
            discharge_id,
            call_id,
            metadata,
            commit,
        )

    existing = TimelineEvent.query.filter_by(
        call_id=call_id, event_type=event_type
    ).first()
    if existing is not None:
        return existing

    return log_event(
        event_type=event_type,
        title=title,
        description=description,
        patient_id=patient_id,
        discharge_id=discharge_id,
        call_id=call_id,
        metadata=metadata,
        commit=commit,
    )


def get_timeline(patient_id: Optional[int] = None, limit: int = 100):
    """
    Fetch timeline events in chronological order (oldest first — reads
    naturally as a story), optionally scoped to one patient.
    """
    query = TimelineEvent.query
    if patient_id is not None:
        query = query.filter_by(patient_id=patient_id)

    return query.order_by(TimelineEvent.created_at.asc()).limit(limit).all()
