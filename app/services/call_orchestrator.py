"""Coordinate follow-up calls, result review, scoring, and escalation.

The live webhook route resolves provider state before passing an event
here. Complete, valid answers proceed to scoring and summary generation;
unusable answers are preserved for review. Timeline entries record each
workflow transition.
"""
from datetime import datetime
from typing import Any, Dict

from app.extensions import db, logger, utcnow
from app.models.call import FollowUpCall
from app.models.discharge import Discharge
from app.models.risk_assessment import RiskAssessment
from app.services import timeline_service
from app.services.answer_normalization import assess_result_quality
from app.services.calle.base import (
    CallRequest,
    ProviderCallBindingError,
    TerminalEvidenceConflictError,
    VoiceProviderClient,
    WebhookEvent,
)
from app.services.care_summary import generate_and_store_summary
from app.services.escalation_service import trigger_escalation
from app.services.notifications.base import NotificationService
from app.services.notifications.log_notifier import LogNotificationService
from app.services.recovery_questions import STANDARD_RECOVERY_QUESTIONS
from app.services.risk_engine import assess_risk


def build_call_idempotency_key(call_id: int, initiated_at: datetime) -> str:
    """Return a stable, attempt-unique CALL-E Create Call key."""
    if call_id is None or initiated_at is None:
        raise ValueError("A flushed call ID and initiation timestamp are required")

    timestamp = initiated_at.strftime("%Y%m%dT%H%M%S%f")
    return f"careflow-call-{call_id}-{timestamp}"


class CallOrchestrator:
    def __init__(self, voice_client: VoiceProviderClient, notification_service: NotificationService = None):
        self.voice_client = voice_client
        # Defaults to the log-based stub so existing call sites (and tests)
        # that don't care about notifications keep working unchanged.
        self.notification_service = notification_service or LogNotificationService()

    def initiate_follow_up_call(self, discharge: Discharge) -> FollowUpCall:
        """Create a FollowUpCall row and ask the voice provider to place the call."""
        call = FollowUpCall(discharge_id=discharge.id, status="initiated")
        db.session.add(call)
        db.session.flush()  # assigns call.id, needed as the reference_id below

        call_request = CallRequest(
            patient_name=discharge.patient.full_name,
            phone_number=discharge.patient.phone_number,
            discharge_diagnosis=discharge.diagnosis,
            questions=STANDARD_RECOVERY_QUESTIONS,
            reference_id=str(call.id),
            idempotency_key=build_call_idempotency_key(call.id, call.initiated_at),
            metadata={"discharge_id": discharge.id},
        )

        try:
            result = self.voice_client.initiate_call(call_request)
            call.provider_call_id = result.provider_call_id
            call.status = "in_progress"
            discharge.status = "call_scheduled"
            logger.info("Call %s initiated via provider (provider_call_id=%s)", call.id, result.provider_call_id)

            timeline_service.log_event(
                event_type="calle_follow_up_initiated",
                title=f"CALL-E follow-up initiated for {discharge.patient.full_name}",
                description=f"Diagnosis: {discharge.diagnosis}",
                patient_id=discharge.patient_id,
                discharge_id=discharge.id,
                call_id=call.id,
                metadata={"provider_call_id": result.provider_call_id},
                commit=False,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any provider failure must not crash the request
            call.status = "failed"
            call.failure_reason = str(exc)
            logger.error("Failed to initiate call %s: %s", call.id, exc)

            timeline_service.log_event(
                event_type="calle_follow_up_failed",
                title=f"CALL-E follow-up failed to initiate for {discharge.patient.full_name}",
                description=str(exc),
                patient_id=discharge.patient_id,
                discharge_id=discharge.id,
                call_id=call.id,
                commit=False,
            )

        db.session.commit()
        return call

    def process_webhook_event(self, raw_payload: Dict[str, Any]) -> FollowUpCall:
        """
        Process a provider-neutral payload used by Demo Mode and local tests.

        The live HTTP webhook route does not call this method: it first asks
        the provider to resolve the untrusted envelope from authoritative GET
        state, then passes the resulting WebhookEvent to ``process_event``.
        """
        event = self.voice_client.parse_webhook_event(raw_payload)
        return self.process_event(event)

    def process_event(self, event: WebhookEvent) -> FollowUpCall:
        """Idempotently apply one trusted, provider-neutral terminal event."""

        call = FollowUpCall.query.filter_by(provider_call_id=event.provider_call_id).first()
        if call is None:
            logger.error("Webhook received for unknown provider_call_id=%s", event.provider_call_id)
            raise ValueError(f"No FollowUpCall found for provider_call_id={event.provider_call_id}")

        self._validate_provider_binding(call, event)
        patient_id = call.discharge.patient_id

        if event.event_type == "result_validation_failed":
            return self._mark_result_for_review(
                call,
                event,
                event.failure_reason or "CALL-E reported structured-result validation failure",
            )

        if event.event_type == "call_completed":
            assessed_evidence = call.risk_assessment is not None
            if assessed_evidence and call.structured_answers != event.structured_answers:
                raise TerminalEvidenceConflictError(
                    "Authenticated terminal answers conflict with previously assessed evidence"
                )

            quality = assess_result_quality(event.structured_answers)
            if quality.requires_review:
                return self._mark_result_for_review(
                    call,
                    event,
                    f"Structured result incomplete or invalid ({quality.issue_summary()})",
                )

            call.status = "completed"
            if not assessed_evidence:
                call.structured_answers = event.structured_answers
                call.transcript = event.transcript
            call.failure_reason = None
            call.completed_at = call.completed_at or utcnow()
            call.discharge.status = "call_completed"

            timeline_service.log_event_once(
                event_type="call_completed",
                title=f"Follow-up call completed with {call.discharge.patient.full_name}",
                description="Structured recovery answers captured.",
                patient_id=patient_id,
                discharge_id=call.discharge_id,
                call_id=call.id,
                commit=False,
            )
            db.session.commit()

            self._run_risk_assessment(call)
        elif event.event_type in {"call_failed", "no_answer"}:
            terminal_status = "failed" if event.event_type == "call_failed" else "no_answer"
            if call.status == "completed" and call.risk_assessment is not None:
                raise ValueError("Refusing to replace an already processed clinical completion")
            call.status = terminal_status
            call.failure_reason = event.failure_reason

            timeline_service.log_event_once(
                event_type="call_not_completed",
                title=f"Call ended without completion ({call.status})",
                description=event.failure_reason or "",
                patient_id=patient_id,
                discharge_id=call.discharge_id,
                call_id=call.id,
                commit=False,
            )
            db.session.commit()
            logger.warning("Call %s ended without completion: %s", call.id, call.status)
        else:
            raise ValueError(f"Unsupported terminal event type: {event.event_type}")

        return call

    @staticmethod
    def _validate_provider_binding(call: FollowUpCall, event: WebhookEvent) -> None:
        """Bind fetched provider identity (and metadata when returned) to this row."""
        if event.provider_call_id != call.provider_call_id:
            raise ProviderCallBindingError("Fetched call ID does not match local provider_call_id")

        metadata = event.provider_metadata
        if not event.requires_careflow_metadata:
            return

        if not isinstance(metadata, dict):
            raise ProviderCallBindingError(
                "Authenticated CALL-E snapshot is missing required CareFlow metadata"
            )

        if "reference_id" not in metadata or "discharge_id" not in metadata:
            raise ProviderCallBindingError(
                "Authenticated CALL-E snapshot is missing required CareFlow metadata"
            )

        reference_id = metadata.get("reference_id")
        if str(reference_id) != str(call.id):
            raise ProviderCallBindingError("CALL-E reference_id does not match the local call")

        discharge_id = metadata.get("discharge_id")
        if str(discharge_id) != str(call.discharge_id):
            raise ProviderCallBindingError("CALL-E discharge_id does not match the local discharge")

    def _mark_result_for_review(
        self, call: FollowUpCall, event: WebhookEvent, reason: str
    ) -> FollowUpCall:
        """
        Preserve an untrustworthy terminal result without interpreting it.

        This is a data-quality outcome, not a clinical risk classification:
        no RiskAssessment or normal CareSummary is generated. Raw provider
        answers remain stored exactly as received for human review/audit.
        """
        if call.risk_assessment is not None or call.care_summary is not None:
            raise ValueError("Refusing to replace existing clinical artifacts with a review result")

        call.status = "needs_review"
        call.structured_answers = event.structured_answers
        call.transcript = event.transcript
        call.failure_reason = reason[:200]
        call.completed_at = call.completed_at or utcnow()
        call.discharge.status = "needs_review"

        timeline_service.log_event_once(
            event_type="call_result_requires_review",
            title=f"Follow-up result requires human review for {call.discharge.patient.full_name}",
            description=reason,
            patient_id=call.discharge.patient_id,
            discharge_id=call.discharge_id,
            call_id=call.id,
            commit=False,
        )
        db.session.commit()
        logger.warning("Call %s requires human review: %s", call.id, reason)
        return call

    def _run_risk_assessment(self, call: FollowUpCall) -> RiskAssessment:
        """Resume the completed-call workflow from whichever artifacts exist."""
        patient = call.discharge.patient

        assessment = RiskAssessment.query.filter_by(call_id=call.id).first()
        if assessment is None:
            result = assess_risk(call.structured_answers or {})
            assessment = RiskAssessment(
                call_id=call.id,
                risk_level=result.risk_level,
                score=result.score,
                reasons=result.reasons,
            )
            db.session.add(assessment)
            db.session.flush()

            logger.info(
                "Call %s assessed as %s risk (score=%s)",
                call.id,
                result.risk_level,
                result.score,
            )

            db.session.commit()

        timeline_service.log_event_once(
            event_type="risk_assessment_generated",
            title=f"Risk assessment generated for {patient.full_name}: {assessment.risk_level.upper()}",
            description=f"Score {assessment.score}. Reasons: {', '.join(assessment.reasons)}",
            patient_id=patient.id,
            discharge_id=call.discharge_id,
            call_id=call.id,
            metadata={"risk_level": assessment.risk_level, "score": assessment.score},
            commit=False,
        )
        db.session.commit()

        if assessment.risk_level == "high":
            # trigger_escalation reads assessment.escalation once it exists,
            # so it must run before the care summary is generated below —
            # otherwise the summary's escalation_status would read "none"
            # even for a patient who was in fact escalated.
            trigger_escalation(assessment, notification_service=self.notification_service)

        generate_and_store_summary(call)
        db.session.commit()

        return assessment
