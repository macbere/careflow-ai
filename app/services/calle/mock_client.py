"""Mock voice provider client.

Simulates CALL-E without placing a real phone call or consuming CALL-E credits. It emits provider-neutral structured outcomes so the downstream CareFlow orchestration, risk, escalation, summary, and review paths can be exercised deterministically.

Scenario answers use the same string contract consumed by the real integration, including explicit unknown values.
"""
import json
import random
import uuid
from typing import Any, Dict

from app.extensions import logger
from app.services.calle.base import (
    CallInitiationResult,
    CallRequest,
    VoiceProviderClient,
    WebhookEvent,
)


def _yes_no(value: bool) -> str:
    """Convert a Python boolean to the provider-neutral yes/no string contract."""
    return "yes" if value else "no"


class MockVoiceClient(VoiceProviderClient):
    """
    Simulates a CALL-E call synchronously for demo purposes.

    In a real deployment, `initiate_call` returns immediately and the
    provider calls our webhook later, asynchronously. To keep the mock
    simple and demo-friendly, `simulate_completed_call` can be called right
    after `initiate_call` to produce the webhook payload — the orchestrator
    treats both paths identically.
    """

    def initiate_call(self, call_request: CallRequest) -> CallInitiationResult:
        provider_call_id = f"mock-{uuid.uuid4().hex[:12]}"
        logger.info(
            "MockVoiceClient: simulating outbound call to %s (ref=%s, call_id=%s)",
            call_request.phone_number,
            call_request.reference_id,
            provider_call_id,
        )
        return CallInitiationResult(provider_call_id=provider_call_id, status="initiated")

    def simulate_completed_call(
        self, provider_call_id: str, call_request: CallRequest, scenario: str = "random"
    ) -> Dict[str, Any]:
        """
        Build a synthetic webhook payload as if the call had just finished.

        `scenario` lets callers/tests force a specific, deterministic outcome.
        Recovery-outcome scenarios (produce a completed call with structured
        answers, now string-typed using the provider string contract):
          - "healthy_recovery" (alias "low_risk"): all-clear answers
          - "moderate_concern": answers that land in the medium-risk band
          - "high_risk": answers that should trigger escalation
          - "random": randomly generated, weighted toward low risk

        Failure scenarios (produce a call that never completed — no
        structured_answers, no risk assessment, matching what a real failed
        or unanswered call looks like — unchanged by the string representation):
          - "failed_call": the call could not be connected
          - "no_answer": the patient never picked up
        """
        if scenario == "failed_call":
            return {
                "provider_call_id": provider_call_id,
                "event_type": "call_failed",
                "failure_reason": "Provider error: call could not be connected (simulated).",
            }

        if scenario == "no_answer":
            return {
                "provider_call_id": provider_call_id,
                "event_type": "no_answer",
                "failure_reason": "Patient did not answer after maximum retry attempts (simulated).",
            }

        if scenario in ("healthy_recovery", "low_risk"):
            answers = {
                "pain_level": str(random.randint(0, 3)),
                "fever": _yes_no(False),
                "medication_collected": _yes_no(True),
                "medication_taken": _yes_no(True),
                "bleeding": _yes_no(False),
                "swelling": _yes_no(False),
                "difficulty_breathing": _yes_no(False),
                "general_recovery": "improving",
            }
        elif scenario == "moderate_concern":
            answers = {
                "pain_level": str(random.randint(5, 6)),
                "fever": _yes_no(True),
                "medication_collected": _yes_no(True),
                "medication_taken": _yes_no(True),
                "bleeding": _yes_no(False),
                "swelling": _yes_no(random.choice([True, False])),
                "difficulty_breathing": _yes_no(False),
                "general_recovery": "about the same",
            }
        elif scenario == "high_risk":
            answers = {
                "pain_level": str(random.randint(8, 10)),
                "fever": _yes_no(True),
                "medication_collected": _yes_no(True),
                "medication_taken": _yes_no(True),
                "bleeding": _yes_no(random.choice([True, False])),
                "swelling": _yes_no(random.choice([True, False])),
                "difficulty_breathing": _yes_no(True),
                "general_recovery": "getting worse",
            }
        else:  # "random"
            answers = {
                "pain_level": str(random.randint(0, 10)),
                "fever": _yes_no(random.random() < 0.2),
                "medication_collected": _yes_no(random.random() < 0.9),
                "medication_taken": _yes_no(random.random() < 0.85),
                "bleeding": _yes_no(random.random() < 0.1),
                "swelling": _yes_no(random.random() < 0.15),
                "difficulty_breathing": _yes_no(random.random() < 0.1),
                "general_recovery": random.choice(["improving", "about the same", "getting worse"]),
            }

        transcript_lines = [
            f"Agent: {q.prompt}\nPatient: {answers[q.key]}" for q in call_request.questions
        ]

        return {
            "provider_call_id": provider_call_id,
            "event_type": "call_completed",
            "structured_answers": answers,
            "transcript": "\n\n".join(transcript_lines),
        }

    def parse_webhook_event(self, raw_payload: Dict[str, Any]) -> WebhookEvent:
        return WebhookEvent(
            provider_call_id=raw_payload["provider_call_id"],
            event_type=raw_payload.get("event_type", "call_completed"),
            structured_answers=raw_payload.get("structured_answers"),
            transcript=raw_payload.get("transcript"),
            failure_reason=raw_payload.get("failure_reason"),
        )

    def resolve_webhook_event(self, headers: Dict[str, str], raw_body: bytes) -> WebhookEvent:
        """Parse only local mock payloads; production trust is implemented by CALL-E."""
        return self.parse_webhook_event(json.loads(raw_body))

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        # No real signature to verify in mock mode.
        return True
