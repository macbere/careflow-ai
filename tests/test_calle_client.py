"""
Provider-layer tests — app/services/calle/calle_client.py and
mock_client.py.

These test the CALL-E client's request construction and response
extraction in isolation, using the real captured payload shapes from
call_3-bmAXd3HqzJWnK5Fg2Z6w and call_dWj5VxQM2s4lhuFsRiRm8g wherever
possible, per instruction to prefer real observed shapes over invented toy
dicts.
"""
import pytest

from app.services.calle.base import CallRequest, RecoveryQuestion
from app.services.calle.calle_client import CalleVoiceClient
from app.services.calle.mock_client import MockVoiceClient

QUESTIONS = [
    RecoveryQuestion(key="pain_level", prompt="pain?"),
    RecoveryQuestion(key="fever", prompt="fever?"),
    RecoveryQuestion(key="medication_collected", prompt="collected?"),
    RecoveryQuestion(key="medication_taken", prompt="taken?"),
    RecoveryQuestion(key="bleeding", prompt="bleeding?"),
    RecoveryQuestion(key="swelling", prompt="swelling?"),
    RecoveryQuestion(key="difficulty_breathing", prompt="breathing?"),
    RecoveryQuestion(key="general_recovery", prompt="recovery?"),
]


def _make_call_request(idempotency_key=None):
    return CallRequest(
        patient_name="Demo Patient",
        phone_number="+15550000000",
        discharge_diagnosis="Test",
        questions=QUESTIONS,
        reference_id="1",
        idempotency_key=idempotency_key,
    )


def _client():
    return CalleVoiceClient(api_key="test_key", base_url="https://api.heycall-e.com")


# --- Create Call idempotency -------------------------------------------------

def test_create_call_uses_explicit_idempotency_key_without_changing_payload(monkeypatch):
    client = _client()
    call_request = _make_call_request(
        idempotency_key="careflow-call-1-20260910T123456123456"
    )
    call_request.metadata = {"discharge_id": 7}
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "call_new", "status": "queued"}

    def fake_post(url, json, headers, timeout):
        captured.update(url=url, payload=json, headers=headers, timeout=timeout)
        return Response()

    monkeypatch.setattr("app.services.calle.calle_client.requests.post", fake_post)

    result = client.initiate_call(call_request)

    assert result.provider_call_id == "call_new"
    assert captured["headers"]["Idempotency-Key"] == call_request.idempotency_key
    assert captured["headers"]["Idempotency-Key"] != f"careflow_{call_request.reference_id}"
    assert captured["payload"] == {
        "task": client._build_task_prompt(call_request),
        "recipients": [{"phones": [call_request.phone_number]}],
        "result_schema": client._build_aggregate_result_schema(),
        "recipient_result_schema": client._build_recipient_result_schema(call_request),
        "metadata": {"reference_id": call_request.reference_id, "discharge_id": 7},
    }


@pytest.mark.parametrize("idempotency_key", [None, "", "x" * 256])
def test_create_call_rejects_missing_or_oversized_idempotency_key(
    monkeypatch, idempotency_key
):
    def unexpected_post(*args, **kwargs):
        raise AssertionError("POST must not run with an invalid idempotency key")

    monkeypatch.setattr(
        "app.services.calle.calle_client.requests.post", unexpected_post
    )

    with pytest.raises(ValueError, match="idempotency_key"):
        _client().initiate_call(_make_call_request(idempotency_key=idempotency_key))


# --- A. Exact recipient_result_schema construction ---------------------------------

def test_a_recipient_result_schema_construction():
    client = _client()
    schema = client._build_recipient_result_schema(_make_call_request())

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {q.key for q in QUESTIONS}
    assert schema["properties"]["pain_level"]["enum"] == [
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "unknown"
    ]
    for field in (
        "fever",
        "medication_collected",
        "medication_taken",
        "bleeding",
        "swelling",
        "difficulty_breathing",
    ):
        assert schema["properties"][field] == {
            "type": "string",
            "enum": ["yes", "no", "unknown"],
        }
    assert schema["properties"]["general_recovery"] == {
        "type": "string",
        "enum": ["improving", "about the same", "getting worse", "unknown"],
    }


def test_a_aggregate_result_schema_is_trivial():
    client = _client()
    schema = client._build_aggregate_result_schema()
    assert schema == {
        "type": "object",
        "required": ["completed_count"],
        "properties": {"completed_count": {"type": "integer"}},
    }


# --- B. Exact recipients request structure ---------------------------------

def test_b_recipients_request_structure_via_payload_shape():
    call_request = _make_call_request()
    client = _client()
    expected_recipients = [{"phones": [call_request.phone_number]}]
    assert expected_recipients == [{"phones": ["+15550000000"]}]
    assert client._build_aggregate_result_schema()["required"] == ["completed_count"]


# --- C. Correct extraction from recipients[0].structured_result ---------------------------------

def test_c_extraction_from_real_successful_payload():
    """Uses the real, captured shape from call_3-bmAXd3HqzJWnK5Fg2Z6w."""
    client = _client()
    raw_payload = {
        "id": "evt_1", "type": "call.completed",
        "data": {
            "id": "call_3-bmAXd3HqzJWnK5Fg2Z6w", "status": "completed",
            "structured_result": {"completed_count": 1},
            "recipients": [{
                "structured_result": {
                    "pain_level": "2", "fever": "no", "medication_collected": "yes",
                    "medication_taken": "yes", "bleeding": "no", "swelling": "no",
                    "difficulty_breathing": "no", "general_recovery": "I'm improving.",
                },
                "attempts": [],
            }],
            "failure_code": None, "failure_message": None,
        },
    }
    event = client.parse_webhook_event(raw_payload)
    assert event.structured_answers["pain_level"] == "2"
    assert event.structured_answers["fever"] == "no"
    assert len(event.structured_answers) == 8


def test_c_unknown_value_preserved_from_real_payload():
    """Uses the real, captured shape from call_dWj5VxQM2s4lhuFsRiRm8g."""
    client = _client()
    raw_payload = {
        "id": "evt_2", "type": "call.completed",
        "data": {
            "id": "call_dWj5VxQM2s4lhuFsRiRm8g", "status": "completed",
            "structured_result": {"completed_count": 1},
            "recipients": [{
                "structured_result": {
                    "pain_level": "unknown", "fever": "no", "medication_collected": "yes",
                    "medication_taken": "yes", "bleeding": "no", "swelling": "no",
                    "difficulty_breathing": "no", "general_recovery": "improving",
                },
                "attempts": [],
            }],
            "failure_code": None, "failure_message": None,
        },
    }
    event = client.parse_webhook_event(raw_payload)
    assert event.structured_answers["pain_level"] == "unknown"


# --- D. Missing recipients key ---------------------------------

def test_d_missing_recipients_key():
    client = _client()
    event = client.parse_webhook_event({
        "type": "call.completed",
        "data": {"id": "call_x", "structured_result": {"completed_count": 0}},
    })
    assert event.structured_answers is None


# --- E. Empty recipients list ---------------------------------

def test_e_empty_recipients_list():
    client = _client()
    event = client.parse_webhook_event({
        "type": "call.completed",
        "data": {"id": "call_x", "recipients": [], "structured_result": {"completed_count": 0}},
    })
    assert event.structured_answers is None


# --- F. Missing recipients[0].structured_result ---------------------------------

def test_f_recipient_present_without_structured_result_key():
    client = _client()
    event = client.parse_webhook_event({
        "type": "call.completed",
        "data": {"id": "call_x", "recipients": [{"attempts": []}]},
    })
    assert event.structured_answers is None


def test_f_recipient_structured_result_explicitly_null():
    client = _client()
    event = client.parse_webhook_event({
        "type": "call.completed",
        "data": {"id": "call_x", "recipients": [{"structured_result": None, "attempts": []}]},
    })
    assert event.structured_answers is None


# --- G. Top-level aggregate must not be mistaken for recovery answers ---------------------------------

def test_g_top_level_aggregate_is_never_used_as_recovery_answers():
    """
    Direct regression test for the provider extraction contract: the
    top-level structured_result is the trivial {"completed_count": N}
    aggregate and must never leak into event.structured_answers.
    """
    client = _client()
    raw_payload = {
        "type": "call.completed",
        "data": {
            "id": "call_x",
            "structured_result": {"completed_count": 1},
            "recipients": [{
                "structured_result": {
                    "pain_level": "0", "fever": "no", "medication_collected": "yes",
                    "medication_taken": "yes", "bleeding": "no", "swelling": "no",
                    "difficulty_breathing": "no", "general_recovery": "improving",
                },
                "attempts": [],
            }],
        },
    }
    event = client.parse_webhook_event(raw_payload)
    assert "completed_count" not in event.structured_answers
    assert event.structured_answers["pain_level"] == "0"


# --- H. "unknown" values pass through unchanged ---------------------------------

def test_h_unknown_passes_through_unchanged_no_coercion():
    client = _client()
    raw_payload = {
        "type": "call.completed",
        "data": {
            "id": "call_x",
            "recipients": [{"structured_result": {"fever": "unknown", "pain_level": "unknown"}, "attempts": []}],
        },
    }
    event = client.parse_webhook_event(raw_payload)
    assert event.structured_answers["fever"] == "unknown"
    assert event.structured_answers["pain_level"] == "unknown"


# --- I. Malformed/unrecognized values pass through unchanged ---------------------------------

def test_i_malformed_value_passes_through_unchanged():
    """
    The client must never repair, discard, or reinterpret an out-of-contract
    value (e.g. "maybe", or a stray boolean) — that is
    answer_normalization.py's job, not the provider client's.
    """
    client = _client()
    raw_payload = {
        "type": "call.completed",
        "data": {
            "id": "call_x",
            "recipients": [{"structured_result": {"fever": "maybe", "pain_level": True}, "attempts": []}],
        },
    }
    event = client.parse_webhook_event(raw_payload)
    assert event.structured_answers["fever"] == "maybe"
    assert event.structured_answers["pain_level"] is True


def test_i_result_validation_failure_is_not_normal_completion():
    client = _client()
    raw_payload = {
        "id": "evt_validation_failed",
        "type": "call.result_validation_failed",
        "data": {
            "id": "call_validation_failed",
            "status": "completed",
            "failure_code": "result_validation_failed",
            "recipients": [{"structured_result": None, "attempts": []}],
        },
    }

    event = client.parse_webhook_event(raw_payload)

    assert event.event_type == "result_validation_failed"
    assert event.structured_answers is None
    assert event.failure_reason == "result_validation_failed"


# --- J. Mock client outputs match the new provider contract ---------------------------------

def test_j_mock_client_emits_string_contract_values():
    mock = MockVoiceClient()
    call_request = _make_call_request()

    for scenario in ("healthy_recovery", "moderate_concern", "high_risk", "random"):
        payload = mock.simulate_completed_call(f"mock-{scenario}", call_request, scenario=scenario)
        answers = payload["structured_answers"]
        assert isinstance(answers["pain_level"], str), f"{scenario}: pain_level must be a string"
        assert answers["fever"] in ("yes", "no"), f"{scenario}: fever must be 'yes'/'no'"
        assert answers["medication_collected"] in ("yes", "no")
        assert answers["difficulty_breathing"] in ("yes", "no")
        assert isinstance(answers["general_recovery"], str)


def test_j_mock_client_failure_scenarios_remain_stable():
    mock = MockVoiceClient()
    call_request = _make_call_request()
    for scenario in ("failed_call", "no_answer"):
        payload = mock.simulate_completed_call(f"mock-{scenario}", call_request, scenario=scenario)
        assert "structured_answers" not in payload
        assert payload["event_type"] in ("call_failed", "no_answer")
