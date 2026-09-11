"""
Escalation service.

Depends only on the abstract NotificationService interface (Phase 2
refactor) — never on a concrete channel. Also logs an "Escalation
Triggered" and "Notification Sent" timeline event pair, since escalation is
one of the most important moments in the whole workflow to have visible in
the chronological feed.
"""

from app.extensions import db, logger, utcnow
from app.models.escalation import EscalationEvent
from app.models.risk_assessment import RiskAssessment
from app.services.notifications.base import NotificationRequest, NotificationService
from app.services.notifications.log_notifier import LogNotificationService
from app.services import timeline_service


def trigger_escalation(
    risk_assessment: RiskAssessment, notification_service: NotificationService = None
) -> EscalationEvent:
    """
    Create an escalation event for a high-risk assessment and send the
    notification through whichever NotificationService is provided (or a
    LogNotificationService by default).

    Only call this for risk_level == "high" — the orchestrator is
    responsible for that decision; this function assumes it's already been
    made, so escalation logic stays testable in isolation.
    """
    notification_service = notification_service or LogNotificationService()

    # The escalation row is the durable send claim. Any replay returns it
    # without invoking the notifier again, preventing duplicate clinical
    # notifications for both same-event and different-event redelivery.
    existing = EscalationEvent.query.filter_by(
        risk_assessment_id=risk_assessment.id
    ).first()
    if existing is not None:
        return existing

    call = risk_assessment.call
    patient = call.discharge.patient

    event = EscalationEvent(risk_assessment_id=risk_assessment.id, status="triggered")
    db.session.add(event)
    db.session.flush()  # get event.id without a full commit yet

    timeline_service.log_event_once(
        event_type="escalation_triggered",
        title=f"Escalation triggered for {patient.full_name}",
        description=f"Risk score {risk_assessment.score} ({', '.join(risk_assessment.reasons)})",
        patient_id=patient.id,
        discharge_id=call.discharge_id,
        call_id=call.id,
        metadata={"risk_assessment_id": risk_assessment.id},
        commit=False,
    )

    request = NotificationRequest(
        subject=f"High-risk follow-up: {patient.full_name}",
        message=(
            f"Patient {patient.full_name} was assessed as HIGH RISK "
            f"(score={risk_assessment.score}) after their follow-up call. "
            f"Reasons: {', '.join(risk_assessment.reasons)}. Nurse review needed."
        ),
        recipient_hint="on_call_nurse",
        metadata={"risk_assessment_id": risk_assessment.id, "call_id": call.id},
    )
    result = notification_service.send(request)

    event.status = "notified" if result.success else "triggered"
    event.action_taken = result.detail or f"Notification sent via {result.channel}"
    event.notified_at = utcnow() if result.success else None

    timeline_service.log_event_once(
        event_type="notification_sent",
        title=f"Notification sent via {result.channel}",
        description=event.action_taken,
        patient_id=patient.id,
        discharge_id=call.discharge_id,
        call_id=call.id,
        metadata={"escalation_event_id": event.id, "success": result.success},
        commit=False,
    )

    db.session.commit()
    logger.info("Escalation %s resolved with status=%s", event.id, event.status)
    return event


def acknowledge_escalation(
    escalation: EscalationEvent, acknowledged_by: str = "on_call_nurse", note: str = None
) -> EscalationEvent:
    """
    Complete the escalation lifecycle: triggered -> notified -> acknowledged.

    This is the human-in-the-loop closing step — someone (a nurse, in the
    real workflow) has reviewed the escalation and confirmed it's been
    handled. Idempotent: calling this twice on an already-acknowledged
    escalation just returns it unchanged rather than erroring, since a
    double-click in the dashboard shouldn't be a failure case.
    """
    if escalation.status == "acknowledged":
        return escalation

    escalation.status = "acknowledged"
    escalation.acknowledged_at = utcnow()
    escalation.acknowledged_by = acknowledged_by
    escalation.acknowledgement_note = note
    db.session.flush()

    call = escalation.risk_assessment.call
    patient = call.discharge.patient

    timeline_service.log_event(
        event_type="escalation_acknowledged",
        title=f"Escalation acknowledged for {patient.full_name}",
        description=note or f"Acknowledged by {acknowledged_by}",
        patient_id=patient.id,
        discharge_id=call.discharge_id,
        call_id=call.id,
        metadata={"escalation_event_id": escalation.id, "acknowledged_by": acknowledged_by},
        commit=False,
    )

    db.session.commit()
    logger.info("Escalation %s acknowledged by %s", escalation.id, acknowledged_by)
    return escalation
