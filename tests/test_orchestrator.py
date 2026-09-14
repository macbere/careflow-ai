"""Integration tests for the mock-provider follow-up workflow.

Cover call initiation, event processing, result review, scoring, escalation,
summary generation, and timeline updates.
"""
from datetime import datetime

import pytest

from app.models.discharge import Discharge
from app.models.escalation import EscalationEvent
from app.models.call import FollowUpCall
from app.models.patient import Patient
from app.services.call_orchestrator import CallOrchestrator, build_call_idempotency_key
from app.services.calle.base import CallRequest
from app.services.calle.mock_client import MockVoiceClient
from app.services.recovery_questions import STANDARD_RECOVERY_QUESTIONS
from app.services.timeline_service import get_timeline


def _make_discharge(db):
    patient = Patient(full_name="Demo Patient Y", synthetic_mrn="SYN-TEST-2", phone_number="+15550008888")
    db.session.add(patient)
    db.session.flush()
    discharge = Discharge(patient_id=patient.id, diagnosis="Test surgery")
    db.session.add(discharge)
    db.session.commit()
    return discharge


def test_idempotency_key_is_attempt_unique_stable_and_non_sensitive():
    phone_number = "+15550008888"
    first_timestamp = datetime(2026, 9, 10, 12, 34, 56, 123456)
    second_timestamp = datetime(2026, 9, 10, 12, 34, 56, 123457)

    first_key = build_call_idempotency_key(1, first_timestamp)
    reconstructed_key = build_call_idempotency_key(1, first_timestamp)
    distinct_attempt_key = build_call_idempotency_key(1, second_timestamp)

    assert first_key == reconstructed_key
    assert first_key != distinct_attempt_key
    assert first_key == "careflow-call-1-20260910T123456123456"
    assert phone_number not in first_key
    assert len(first_key) <= 255


def test_orchestrator_supplies_key_from_flushed_call_attempt(db):
    discharge = _make_discharge(db)

    class RecordingMockClient(MockVoiceClient):
        request = None

        def initiate_call(self, call_request):
            self.request = call_request
            return super().initiate_call(call_request)

    client = RecordingMockClient()
    call = CallOrchestrator(client).initiate_follow_up_call(discharge)
    call_id = call.id
    emitted_key = client.request.idempotency_key

    assert emitted_key == build_call_idempotency_key(
        call.id, call.initiated_at
    )

    db.session.expire_all()
    persisted_call = db.session.get(FollowUpCall, call_id)
    assert build_call_idempotency_key(
        persisted_call.id, persisted_call.initiated_at
    ) == emitted_key


def _initiated_call_with_payload(db, scenario="low_risk"):
    discharge = _make_discharge(db)
    mock_client = MockVoiceClient()
    orchestrator = CallOrchestrator(mock_client)
    call = orchestrator.initiate_follow_up_call(discharge)
    call_request = CallRequest(
        patient_name=discharge.patient.full_name,
        phone_number=discharge.patient.phone_number,
        discharge_diagnosis=discharge.diagnosis,
        questions=STANDARD_RECOVERY_QUESTIONS,
        reference_id=str(call.id),
    )
    payload = mock_client.simulate_completed_call(
        call.provider_call_id, call_request, scenario=scenario
    )
    return orchestrator, call, payload


def _assert_requires_review(call):
    assert call.status == "needs_review"
    assert call.discharge.status == "needs_review"
    assert call.risk_assessment is None
    assert call.care_summary is None
    assert EscalationEvent.query.count() == 0
    event_types = {
        event.event_type for event in get_timeline(patient_id=call.discharge.patient_id)
    }
    assert "call_result_requires_review" in event_types
    assert "risk_assessment_generated" not in event_types


def test_low_risk_call_does_not_escalate(app, db):
    discharge = _make_discharge(db)
    mock_client = MockVoiceClient()
    orchestrator = CallOrchestrator(mock_client)

    call = orchestrator.initiate_follow_up_call(discharge)
    assert call.status == "in_progress"
    assert call.provider_call_id is not None

    call_request = CallRequest(
        patient_name=discharge.patient.full_name,
        phone_number=discharge.patient.phone_number,
        discharge_diagnosis=discharge.diagnosis,
        questions=STANDARD_RECOVERY_QUESTIONS,
        reference_id=str(call.id),
    )
    payload = mock_client.simulate_completed_call(call.provider_call_id, call_request, scenario="low_risk")

    updated_call = orchestrator.process_webhook_event(payload)

    assert updated_call.status == "completed"
    assert updated_call.risk_assessment.risk_level == "low"
    assert updated_call.risk_assessment.escalation is None

    # Low-risk completion has a summary without an escalation.
    assert updated_call.care_summary is not None
    assert updated_call.care_summary.escalation_status == "none"

    # Each completed workflow stage has a timeline event.
    events = get_timeline(patient_id=updated_call.discharge.patient_id)
    event_types = {e.event_type for e in events}
    assert "calle_follow_up_initiated" in event_types
    assert "call_completed" in event_types
    assert "risk_assessment_generated" in event_types


def test_high_risk_call_triggers_escalation(app, db):
    discharge = _make_discharge(db)
    mock_client = MockVoiceClient()
    orchestrator = CallOrchestrator(mock_client)

    call = orchestrator.initiate_follow_up_call(discharge)

    call_request = CallRequest(
        patient_name=discharge.patient.full_name,
        phone_number=discharge.patient.phone_number,
        discharge_diagnosis=discharge.diagnosis,
        questions=STANDARD_RECOVERY_QUESTIONS,
        reference_id=str(call.id),
    )
    payload = mock_client.simulate_completed_call(call.provider_call_id, call_request, scenario="high_risk")

    updated_call = orchestrator.process_webhook_event(payload)

    assert updated_call.risk_assessment.risk_level == "high"
    assert updated_call.risk_assessment.escalation is not None
    assert updated_call.risk_assessment.escalation.status == "notified"

    # The care summary reflects the escalation, and the full event
    # sequence (including escalation + notification) was logged
    assert updated_call.care_summary.escalation_status == "notified"
    event_types = {e.event_type for e in get_timeline(patient_id=updated_call.discharge.patient_id)}
    assert "escalation_triggered" in event_types
    assert "notification_sent" in event_types


def test_empty_structured_result_requires_review(app, db):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload["structured_answers"] = {}

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert call.structured_answers == {}


def test_none_structured_result_requires_review(app, db):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload["structured_answers"] = None

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert call.structured_answers is None


def test_missing_difficulty_breathing_is_not_equivalent_to_no(app, db):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload["structured_answers"].pop("difficulty_breathing")

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert "difficulty_breathing" not in call.structured_answers


def test_explicit_null_is_preserved_and_requires_review(app, db):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload["structured_answers"]["swelling"] = None

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert call.structured_answers["swelling"] is None
    assert "swelling:explicit_null" in call.failure_reason


def test_explicit_unknown_is_preserved_and_requires_review(app, db):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload["structured_answers"]["pain_level"] = "unknown"

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert call.structured_answers["pain_level"] == "unknown"
    assert "pain_level:explicit_unknown" in call.failure_reason

    response = app.test_client().get(f"/dashboard/calls/{call.id}")
    assert response.status_code == 200
    assert b"HUMAN REVIEW REQUIRED" in response.data
    assert b"did not generate an ordinary risk assessment" in response.data


@pytest.mark.parametrize(
    ("field", "malformed_value"),
    [("fever", "maybe"), ("pain_level", "11")],
)
def test_malformed_structured_value_requires_review(app, db, field, malformed_value):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload["structured_answers"][field] = malformed_value

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert call.structured_answers[field] == malformed_value
    assert f"{field}:unrecognized_value" in call.failure_reason


def test_result_validation_failure_skips_risk_and_summary(app, db):
    orchestrator, _, payload = _initiated_call_with_payload(db)
    payload.update(
        event_type="result_validation_failed",
        structured_answers=None,
        failure_reason="result_validation_failed",
    )

    call = orchestrator.process_webhook_event(payload)

    _assert_requires_review(call)
    assert call.failure_reason == "result_validation_failed"
