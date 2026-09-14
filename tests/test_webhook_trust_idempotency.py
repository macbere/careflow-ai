"""Integration tests for authenticated provider results and sequential replay."""
from copy import deepcopy

import pytest

import app.api.webhooks as webhook_api
from app.extensions import utcnow
from app.models.call import FollowUpCall
from app.models.care_summary import CareSummary
from app.models.discharge import Discharge
from app.models.escalation import EscalationEvent
from app.models.patient import Patient
from app.models.risk_assessment import RiskAssessment
from app.models.timeline_event import TimelineEvent
from app.services.calle.calle_client import CalleVoiceClient
from app.services.notifications.base import (
    NotificationRequest,
    NotificationResult,
    NotificationService,
)
from app.services.risk_engine import assess_risk


_MATCHING_METADATA = object()
_COMMON_EVENT_IDS = {
    "evt_phase_b",
    "evt_same",
    "evt_one",
    "evt_two",
    "evt_validation_one",
    "evt_validation_two",
    "evt_fail_one",
    "evt_fail_two",
    "evt_resume",
    "evt_resume_again",
    "evt_forged_validation",
    "evt_forged_completed",
    "evt_call_mismatch",
    "evt_event_error",
    "evt_page_match",
    "evt_metadata_match",
    "evt_wrong_reference",
    "evt_wrong_discharge",
    "evt_missing_metadata",
    "evt_conflict_first",
    "evt_conflict_second",
}


class CountingNotificationService(NotificationService):
    def __init__(self):
        self.sent = []

    def send(self, request: NotificationRequest) -> NotificationResult:
        self.sent.append(request)
        return NotificationResult(success=True, channel="test", detail="sent once")


def _make_call(db, provider_call_id="call_phase_b"):
    patient = Patient(
        full_name="Phase B Patient",
        synthetic_mrn="SYN-PHASE-B",
        phone_number="+15550001234",
    )
    db.session.add(patient)
    db.session.flush()
    discharge = Discharge(patient_id=patient.id, diagnosis="Test recovery")
    db.session.add(discharge)
    db.session.flush()
    call = FollowUpCall(
        discharge_id=discharge.id,
        provider_call_id=provider_call_id,
        status="in_progress",
    )
    db.session.add(call)
    db.session.commit()
    return call


def _low_answers():
    return {
        "pain_level": "2",
        "fever": "no",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "no",
        "general_recovery": "improving",
    }


def _high_answers():
    return {
        "pain_level": "9",
        "fever": "yes",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "yes",
        "swelling": "yes",
        "difficulty_breathing": "yes",
        "general_recovery": "getting worse",
    }


def _snapshot(
    call,
    answers=None,
    status="completed",
    failure_code=None,
    metadata=_MATCHING_METADATA,
    snapshot_call_id=None,
):
    snapshot = {
        "id": snapshot_call_id or call.provider_call_id,
        "status": status,
        "structured_result": {"completed_count": 1},
        "recipients": [
            {
                "structured_result": deepcopy(answers),
                "attempts": [
                    {
                        "transcript_turns": [
                            {"speaker": "patient", "text": "trusted transcript"}
                        ]
                    }
                ],
            }
        ],
        "failure_code": failure_code,
        "failure_message": None,
    }

    if metadata is _MATCHING_METADATA:
        snapshot["metadata"] = {
            "reference_id": str(call.id),
            "discharge_id": call.discharge_id,
        }
    elif metadata is not None:
        snapshot["metadata"] = metadata

    return snapshot


def _developer_event(event_id, call_id, event_type="call.completed", status="completed"):
    return {
        "id": event_id,
        "type": event_type,
        "call_id": call_id,
        "status": status,
    }


def _install_provider(
    monkeypatch,
    snapshot,
    notification_service=None,
    trusted_event_type="call.completed",
    event_pages=None,
    event_error=None,
):
    provider = CalleVoiceClient(
        api_key="test-key", base_url="https://api.heycall-e.invalid"
    )

    def get_call(_call_id):
        if isinstance(snapshot, Exception):
            raise snapshot
        return deepcopy(snapshot)

    if event_pages is None and not isinstance(snapshot, Exception):
        event_pages = {
            None: {
                "object": "list",
                "data": [
                    {
                        "id": event_id,
                        "type": trusted_event_type,
                        "call_id": snapshot["id"],
                        "status": snapshot.get("status"),
                    }
                    for event_id in sorted(_COMMON_EVENT_IDS)
                ],
                "next_cursor": None,
            }
        }

    def get_call_events(_call_id, cursor=None, limit=100):
        if event_error is not None:
            raise event_error
        return deepcopy(event_pages[cursor])

    monkeypatch.setattr(provider, "get_call", get_call)
    monkeypatch.setattr(provider, "get_call_events", get_call_events)
    monkeypatch.setattr(webhook_api, "get_voice_client", lambda _config: provider)
    if notification_service is not None:
        monkeypatch.setattr(
            webhook_api,
            "get_notification_service",
            lambda _config: notification_service,
        )
    return provider


def _post(client, call_id, event_id="evt_phase_b", body_data=None, event_type="call.completed"):
    data = {
        "id": call_id,
        "status": "completed",
        "recipients": [{"structured_result": _high_answers(), "attempts": []}],
        "summary": "forged body summary",
    }
    if body_data:
        data.update(body_data)
    return client.post(
        "/api/webhooks/calle",
        json={"id": event_id, "type": event_type, "data": data},
        headers={"CALL-E-Event-Id": event_id},
    )


def _count_timeline(call, event_type):
    return TimelineEvent.query.filter_by(call_id=call.id, event_type=event_type).count()


def _assert_one_completed_workflow(call, expected_risk, escalation_count):
    assert RiskAssessment.query.filter_by(call_id=call.id).count() == 1
    assert CareSummary.query.filter_by(call_id=call.id).count() == 1
    assert EscalationEvent.query.count() == escalation_count
    assert call.risk_assessment.risk_level == expected_risk
    assert _count_timeline(call, "call_completed") == 1
    assert _count_timeline(call, "risk_assessment_generated") == 1


def test_forged_body_answers_are_overridden_by_authoritative_get(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(monkeypatch, _snapshot(call, _low_answers()))

    response = _post(app.test_client(), call.provider_call_id)

    assert response.status_code == 200
    assert call.structured_answers == _low_answers()
    assert call.risk_assessment.risk_level == "low"


def test_forged_body_transcript_is_overridden_by_authoritative_get(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(monkeypatch, _snapshot(call, _low_answers()))

    response = _post(
        app.test_client(),
        call.provider_call_id,
        body_data={
            "recipients": [
                {
                    "structured_result": _high_answers(),
                    "attempts": [
                        {"transcript_turns": [{"speaker": "attacker", "text": "forged"}]}
                    ],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert call.transcript == "patient: trusted transcript"
    assert "forged" not in call.transcript


def test_body_completion_cannot_override_nonterminal_snapshot(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers(), status="in_progress"),
    )

    response = _post(app.test_client(), call.provider_call_id)

    assert response.status_code == 503
    assert response.get_json()["status"] == "retry"
    assert "deferred" not in response.get_json().values()
    assert call.status == "in_progress"
    assert call.structured_answers is None
    assert RiskAssessment.query.count() == 0
    assert TimelineEvent.query.filter_by(call_id=call.id).count() == 0


def test_fetched_call_id_mismatch_fails_closed(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers(), snapshot_call_id="call_different"),
    )

    response = _post(app.test_client(), call.provider_call_id)

    assert response.status_code == 409
    assert call.status == "in_progress"
    assert RiskAssessment.query.count() == 0
    assert TimelineEvent.query.filter_by(call_id=call.id).count() == 0


def test_same_high_risk_event_replay_has_one_observable_effect(app, db, monkeypatch):
    call = _make_call(db)
    notifier = CountingNotificationService()
    _install_provider(
        monkeypatch,
        _snapshot(call, _high_answers()),
        notifier,
    )

    first = _post(app.test_client(), call.provider_call_id, event_id="evt_same")
    second = _post(app.test_client(), call.provider_call_id, event_id="evt_same")

    assert first.status_code == second.status_code == 200
    _assert_one_completed_workflow(call, "high", 1)
    assert len(notifier.sent) == 1
    assert _count_timeline(call, "escalation_triggered") == 1
    assert _count_timeline(call, "notification_sent") == 1


def test_different_event_ids_for_same_call_have_one_effect(app, db, monkeypatch):
    call = _make_call(db)
    notifier = CountingNotificationService()
    _install_provider(
        monkeypatch,
        _snapshot(call, _high_answers()),
        notifier,
    )

    assert _post(app.test_client(), call.provider_call_id, event_id="evt_one").status_code == 200
    assert _post(app.test_client(), call.provider_call_id, event_id="evt_two").status_code == 200

    _assert_one_completed_workflow(call, "high", 1)
    assert len(notifier.sent) == 1
    assert _count_timeline(call, "escalation_triggered") == 1
    assert _count_timeline(call, "notification_sent") == 1


def test_low_risk_replay_has_one_assessment_and_summary(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(monkeypatch, _snapshot(call, _low_answers()))

    assert _post(app.test_client(), call.provider_call_id).status_code == 200
    assert _post(app.test_client(), call.provider_call_id).status_code == 200

    _assert_one_completed_workflow(call, "low", 0)


def test_needs_review_replay_creates_no_clinical_artifacts(app, db, monkeypatch):
    call = _make_call(db)
    incomplete = _low_answers()
    incomplete.pop("difficulty_breathing")
    _install_provider(monkeypatch, _snapshot(call, incomplete))

    assert _post(app.test_client(), call.provider_call_id).status_code == 200
    assert _post(app.test_client(), call.provider_call_id).status_code == 200

    assert call.status == "needs_review"
    assert RiskAssessment.query.count() == 0
    assert CareSummary.query.count() == 0
    assert EscalationEvent.query.count() == 0
    assert _count_timeline(call, "call_result_requires_review") == 1


@pytest.mark.parametrize("general_recovery", ["declining", "unknown"])
def test_unusable_general_recovery_replay_is_review_only(
    app, db, monkeypatch, general_recovery
):
    call = _make_call(db)
    invalid = _low_answers()
    invalid["general_recovery"] = general_recovery
    _install_provider(monkeypatch, _snapshot(call, invalid))

    assert _post(app.test_client(), call.provider_call_id).status_code == 200
    assert _post(app.test_client(), call.provider_call_id).status_code == 200

    assert call.status == "needs_review"
    assert call.discharge.status == "needs_review"
    assert call.structured_answers["general_recovery"] == general_recovery
    assert RiskAssessment.query.count() == 0
    assert CareSummary.query.count() == 0
    assert EscalationEvent.query.count() == 0
    assert _count_timeline(call, "call_result_requires_review") == 1
    assert _count_timeline(call, "call_completed") == 0
    assert _count_timeline(call, "risk_assessment_generated") == 0


def test_validation_failed_replay_is_review_only(app, db, monkeypatch):
    call = _make_call(db)
    snapshot = _snapshot(
        call,
        None,
        status="failed",
        failure_code="result_validation_failed",
    )
    _install_provider(
        monkeypatch,
        snapshot,
        trusted_event_type="call.result_validation_failed",
    )

    for event_id in ("evt_validation_one", "evt_validation_two"):
        response = _post(
            app.test_client(),
            call.provider_call_id,
            event_id=event_id,
            event_type="call.result_validation_failed",
        )
        assert response.status_code == 200

    assert call.status == "needs_review"
    assert RiskAssessment.query.count() == CareSummary.query.count() == 0
    assert _count_timeline(call, "call_result_requires_review") == 1


@pytest.mark.parametrize(
    "failure_code",
    ["provider_error", "no_answer"],
)
def test_noncompletion_replay_has_one_terminal_timeline(
    app, db, monkeypatch, failure_code
):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, None, status="failed", failure_code=failure_code),
        trusted_event_type="call.failed",
    )

    assert _post(app.test_client(), call.provider_call_id, event_id="evt_fail_one").status_code == 200
    assert _post(app.test_client(), call.provider_call_id, event_id="evt_fail_two").status_code == 200

    assert call.status == "failed"
    assert failure_code in call.failure_reason
    assert RiskAssessment.query.count() == CareSummary.query.count() == 0
    assert _count_timeline(call, "call_not_completed") == 1


def test_replay_repairs_partial_completion_without_duplicates(app, db, monkeypatch):
    call = _make_call(db)
    answers = _high_answers()
    result = assess_risk(answers)
    call.status = "completed"
    call.structured_answers = answers
    call.transcript = "trusted prior transcript"
    call.completed_at = utcnow()
    call.discharge.status = "call_completed"
    db.session.add(
        RiskAssessment(
            call_id=call.id,
            risk_level=result.risk_level,
            score=result.score,
            reasons=result.reasons,
        )
    )
    db.session.commit()

    notifier = CountingNotificationService()
    _install_provider(monkeypatch, _snapshot(call, answers), notifier)

    assert _post(app.test_client(), call.provider_call_id, event_id="evt_resume").status_code == 200
    assert _post(app.test_client(), call.provider_call_id, event_id="evt_resume_again").status_code == 200

    _assert_one_completed_workflow(call, "high", 1)
    assert len(notifier.sent) == 1
    assert _count_timeline(call, "escalation_triggered") == 1
    assert _count_timeline(call, "notification_sent") == 1


def test_forged_validation_type_cannot_override_authenticated_completed_event(
    app, db, monkeypatch
):
    call = _make_call(db)
    _install_provider(monkeypatch, _snapshot(call, _low_answers()))

    response = _post(
        app.test_client(),
        call.provider_call_id,
        event_id="evt_forged_validation",
        event_type="call.result_validation_failed",
    )

    assert response.status_code == 200
    assert call.status == "completed"
    assert call.risk_assessment.risk_level == "low"


def test_forged_completed_type_cannot_override_authenticated_validation_event(
    app, db, monkeypatch
):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers()),
        trusted_event_type="call.result_validation_failed",
    )

    response = _post(
        app.test_client(),
        call.provider_call_id,
        event_id="evt_forged_completed",
        event_type="call.completed",
    )

    assert response.status_code == 200
    assert call.status == "needs_review"
    assert RiskAssessment.query.count() == CareSummary.query.count() == 0


def test_webhook_event_id_must_exist_in_authenticated_event_list(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers()),
        event_pages={None: {"object": "list", "data": [], "next_cursor": None}},
    )

    response = _post(app.test_client(), call.provider_call_id, event_id="evt_missing")

    assert response.status_code == 503
    assert call.status == "in_progress"
    assert TimelineEvent.query.filter_by(call_id=call.id).count() == 0


def test_authenticated_event_call_id_mismatch_is_rejected(app, db, monkeypatch):
    call = _make_call(db)
    mismatched_event = _developer_event(
        "evt_call_mismatch", "call_wrong", event_type="call.completed"
    )
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers()),
        event_pages={
            None: {"object": "list", "data": [mismatched_event], "next_cursor": None}
        },
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_call_mismatch"
    )

    assert response.status_code == 409
    assert call.status == "in_progress"
    assert RiskAssessment.query.count() == 0


def test_authenticated_event_list_failure_fails_closed(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers()),
        event_error=RuntimeError("event endpoint unavailable"),
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_event_error"
    )

    assert response.status_code == 503
    assert call.status == "in_progress"
    assert TimelineEvent.query.filter_by(call_id=call.id).count() == 0


def test_authenticated_event_pagination_finds_exact_event(app, db, monkeypatch):
    call = _make_call(db)
    event_pages = {
        None: {
            "object": "list",
            "data": [_developer_event("evt_older", call.provider_call_id)],
            "next_cursor": "cursor-2",
        },
        "cursor-2": {
            "object": "list",
            "data": [_developer_event("evt_page_match", call.provider_call_id)],
            "next_cursor": None,
        },
    }
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers()),
        event_pages=event_pages,
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_page_match"
    )

    assert response.status_code == 200
    assert call.status == "completed"


def test_matching_live_careflow_metadata_is_accepted(app, db, monkeypatch):
    call = _make_call(db)
    metadata = {"reference_id": str(call.id), "discharge_id": call.discharge_id}
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers(), metadata=metadata),
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_metadata_match"
    )

    assert response.status_code == 200
    assert call.status == "completed"


def test_wrong_live_reference_id_is_rejected_without_mutation(app, db, monkeypatch):
    call = _make_call(db)
    metadata = {"reference_id": "wrong", "discharge_id": call.discharge_id}
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers(), metadata=metadata),
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_wrong_reference"
    )

    assert response.status_code == 409
    assert call.status == "in_progress"
    assert RiskAssessment.query.count() == 0


def test_wrong_live_discharge_id_is_rejected_without_mutation(app, db, monkeypatch):
    call = _make_call(db)
    metadata = {"reference_id": str(call.id), "discharge_id": call.discharge_id + 1}
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers(), metadata=metadata),
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_wrong_discharge"
    )

    assert response.status_code == 409
    assert call.status == "in_progress"
    assert RiskAssessment.query.count() == 0


def test_missing_live_careflow_metadata_is_rejected_without_mutation(
    app, db, monkeypatch
):
    call = _make_call(db)
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers(), metadata=None),
    )

    response = _post(
        app.test_client(), call.provider_call_id, event_id="evt_missing_metadata"
    )

    assert response.status_code == 409
    assert call.status == "in_progress"
    assert RiskAssessment.query.count() == 0


def test_changed_answers_after_assessment_are_rejected_without_corruption(
    app, db, monkeypatch
):
    call = _make_call(db)
    notifier = CountingNotificationService()
    _install_provider(
        monkeypatch,
        _snapshot(call, _low_answers()),
        notifier,
    )
    first = _post(
        app.test_client(), call.provider_call_id, event_id="evt_conflict_first"
    )
    original_answers = deepcopy(call.structured_answers)
    original_assessment_id = call.risk_assessment.id
    original_summary_id = call.care_summary.id
    timeline_count = TimelineEvent.query.filter_by(call_id=call.id).count()

    _install_provider(
        monkeypatch,
        _snapshot(call, _high_answers()),
        notifier,
    )
    conflict = _post(
        app.test_client(), call.provider_call_id, event_id="evt_conflict_second"
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert call.structured_answers == original_answers
    assert call.risk_assessment.id == original_assessment_id
    assert call.risk_assessment.risk_level == "low"
    assert call.care_summary.id == original_summary_id
    assert RiskAssessment.query.count() == CareSummary.query.count() == 1
    assert EscalationEvent.query.count() == 0
    assert len(notifier.sent) == 0
    assert TimelineEvent.query.filter_by(call_id=call.id).count() == timeline_count


def test_authoritative_get_failure_is_retryable_and_has_no_mutation(app, db, monkeypatch):
    call = _make_call(db)
    _install_provider(monkeypatch, RuntimeError("provider unavailable"))

    response = _post(app.test_client(), call.provider_call_id)

    assert response.status_code == 503
    assert call.status == "in_progress"
    assert RiskAssessment.query.count() == 0
    assert TimelineEvent.query.filter_by(call_id=call.id).count() == 0
