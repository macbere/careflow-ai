"""Real CALL-E voice provider client.

The integration follows the documented CALL-E REST contract at
https://docs.heycall-e.com. Recovery-question answers are requested through
recipient_result_schema and read from recipients[0].structured_result.
This provider contract has been validated against genuine CALL-E calls.

CALL-E is goal-driven: the application supplies a natural-language task and
structured result schemas, while this client handles REST-based call
creation, provider-state retrieval, event resolution, and result parsing.
"""
import json
from typing import Any, Dict, List, Optional

import requests

from app.extensions import logger
from app.services.calle.base import (
    AuthoritativeSnapshotUnavailableError,
    CallInitiationResult,
    CallRequest,
    InvalidWebhookEnvelopeError,
    NonterminalSnapshotError,
    ProviderCallBindingError,
    VoiceProviderClient,
    WebhookEvent,
)

# each recovery-question key mapped to its JSON Schema property
# definition for recipient_result_schema — string enums including an
# explicit "unknown" value, matching CALL-E's own documented uncertainty
# pattern (confirmed live in call_dWj5VxQM2s4lhuFsRiRm8g, where
# pain_level="unknown" was returned correctly and preserved end to end).
# This client does not interpret these values in any way — it only
# declares, to CALL-E, the shape of the answer it should return.
# Interpretation is entirely the responsibility of
# app/services/answer_normalization.py downstream (CRITICAL PASS-THROUGH
# RULE: this file must never convert "unknown" to None/False/0, never
# classify pain as reassuring/concerning, never interpret general_recovery).
_RECIPIENT_ANSWER_PROPERTIES = {
    "pain_level": {
        "type": "string",
        "enum": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "unknown"],
    },
    "fever": {"type": "string", "enum": ["yes", "no", "unknown"]},
    "medication_collected": {"type": "string", "enum": ["yes", "no", "unknown"]},
    "medication_taken": {"type": "string", "enum": ["yes", "no", "unknown"]},
    "bleeding": {"type": "string", "enum": ["yes", "no", "unknown"]},
    "swelling": {"type": "string", "enum": ["yes", "no", "unknown"]},
    "difficulty_breathing": {"type": "string", "enum": ["yes", "no", "unknown"]},
    "general_recovery": {
        "type": "string",
        "enum": ["improving", "about the same", "getting worse", "unknown"],
    },
}

# the task-level result_schema is now a trivial aggregate — the
# real recovery answers live in recipient_result_schema instead. This exact
# shape was validated live: both successful calls returned
# {"completed_count": 1} here, never the recovery answers.
_AGGREGATE_RESULT_SCHEMA = {
    "type": "object",
    "required": ["completed_count"],
    "properties": {"completed_count": {"type": "integer"}},
}

# terminal webhook event types, per the Webhooks doc page.
_TERMINAL_EVENT_TYPES = {"call.completed", "call.failed", "call.result_validation_failed"}


class CalleVoiceClient(VoiceProviderClient):
    def __init__(self, api_key: str, base_url: str, webhook_secret: str = "", webhook_url: Optional[str] = None):
        if not api_key:
            raise ValueError(
                "CALLE_API_KEY is not set. Set it in .env or switch "
                "VOICE_PROVIDER=mock for local development without live calls."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.webhook_secret = webhook_secret
        self.webhook_url = webhook_url

    def _build_task_prompt(self, call_request: CallRequest) -> str:
        """Build the CareFlow recovery-check task prompt sent to CALL-E."""
        question_lines = "\n".join(f"- {q.prompt}" for q in call_request.questions)
        return (
            f"You are calling {call_request.patient_name}, a patient recently "
            f"discharged from the hospital with a diagnosis of "
            f"{call_request.discharge_diagnosis}. This is a routine post-discharge "
            f"wellness check. Be warm, empathetic, and brief. Ask the following "
            f"recovery questions in a natural conversational order, and make sure "
            f"you get a clear answer to each before ending the call:\n"
            f"{question_lines}\n\n"
            f"If the patient describes a medical emergency in progress (e.g. "
            f"severe difficulty breathing, chest pain), advise them to hang up "
            f"and call emergency services immediately, then end the call."
        )

    def _build_recipient_result_schema(self, call_request: CallRequest) -> Dict[str, Any]:
        """Build the per-recipient schema for the eight structured recovery answers."""
        properties = {
            q.key: _RECIPIENT_ANSWER_PROPERTIES.get(q.key, {"type": "string"})
            for q in call_request.questions
        }
        return {
            "type": "object",
            "required": [q.key for q in call_request.questions],
            "properties": properties,
            "additionalProperties": False,
        }

    def _build_aggregate_result_schema(self) -> Dict[str, Any]:
        """Return the task-level aggregate completion schema."""
        return dict(_AGGREGATE_RESULT_SCHEMA)

    def initiate_call(self, call_request: CallRequest) -> CallInitiationResult:
        idempotency_key = call_request.idempotency_key
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("CALL-E Create Call requires an explicit idempotency_key")
        if len(idempotency_key) > 255:
            raise ValueError("CALL-E idempotency_key must be at most 255 characters")

        payload = {
            "task": self._build_task_prompt(call_request),
            # `recipients` is a list of {"phones": [...]} objects —
            # confirmed live-accepted (in contrast to the singular `recipient`
            # shape, which live testing confirmed is REJECTED by the current
            # API with HTTP 422 "extra_forbidden"). Do not change this shape.
            "recipients": [{"phones": [call_request.phone_number]}],
            # result_schema is now the trivial task-level aggregate —
            # the recovery-question schema moved to recipient_result_schema.
            "result_schema": self._build_aggregate_result_schema(),
            "recipient_result_schema": self._build_recipient_result_schema(call_request),
            "metadata": {"reference_id": call_request.reference_id, **call_request.metadata},
        }
        if self.webhook_url:
            payload["webhook_url"] = self.webhook_url

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }

        logger.info(
            "CalleVoiceClient: initiating call to %s (ref=%s)",
            call_request.phone_number,
            call_request.reference_id,
        )
        response = requests.post(
            f"{self.base_url}/v1/calls", json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return CallInitiationResult(
            provider_call_id=data["id"],
            status=data.get("status", "initiated"),
        )

    def get_call(self, call_id: str) -> Dict[str, Any]:
        """GET /v1/calls/{id} — fetch a call's current/terminal snapshot."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(f"{self.base_url}/v1/calls/{call_id}", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_call_events(
        self, call_id: str, cursor: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """GET /v1/calls/{id}/events — fetch one authenticated event page."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        response = requests.get(
            f"{self.base_url}/v1/calls/{call_id}/events",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _extract_recipient_structured_result(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return the first recipient's structured recovery result without interpreting, coercing, or repairing values."""
        recipients = data.get("recipients")
        if not isinstance(recipients, list) or not recipients:
            return None

        first_recipient = recipients[0]
        if not isinstance(first_recipient, dict):
            return None

        return first_recipient.get("structured_result")

    def parse_webhook_event(self, raw_payload: Dict[str, Any]) -> WebhookEvent:
        """
        Normalize a CALL-E webhook payload into our internal WebhookEvent shape.

        This parser remains available for captured payload tests and polling
        compatibility. The live HTTP webhook path uses
        ``resolve_webhook_event`` so the inbound body's clinical fields never
        cross the trust boundary.
        """
        data = raw_payload.get("data", {})
        event_type = raw_payload.get("type", "")

        type_map = {
            "call.completed": "call_completed",
            # A terminal transport event, but not a trustworthy clinical
            # completion: the orchestrator routes it to human review and
            # never runs the ordinary risk/summary path.
            "call.result_validation_failed": "result_validation_failed",
            "call.failed": "call_failed",
        }
        normalized_event_type = type_map.get(event_type, "call_failed")

        # read from recipients[0].structured_result, NOT the
        # top-level structured_result (which is now the trivial aggregate).
        structured_answers = self._extract_recipient_structured_result(data)

        transcript = self._extract_transcript(data)
        failure_reason = data.get("failure_message") or data.get("failure_code")

        return WebhookEvent(
            provider_call_id=data.get("id", raw_payload.get("id", "")),
            event_type=normalized_event_type,
            structured_answers=structured_answers,
            transcript=transcript,
            failure_reason=failure_reason,
            provider_event_id=raw_payload.get("id"),
            provider_metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
        )

    def resolve_webhook_event(
        self, headers: Dict[str, str], raw_body: bytes
    ) -> WebhookEvent:
        """Resolve an untrusted webhook wake-up from authenticated GET state."""
        event_id, call_id = self._parse_webhook_envelope(headers, raw_body)

        try:
            snapshot = self.get_call(call_id)
        except Exception as exc:  # noqa: BLE001 - every provider/decoding failure fails closed
            logger.warning("Could not fetch authoritative CALL-E snapshot for %s: %s", call_id, exc)
            raise AuthoritativeSnapshotUnavailableError(
                f"Authoritative CALL-E snapshot unavailable for {call_id}"
            ) from exc

        if not isinstance(snapshot, dict):
            raise AuthoritativeSnapshotUnavailableError(
                f"Authoritative CALL-E snapshot for {call_id} was not an object"
            )
        if snapshot.get("id") != call_id:
            raise ProviderCallBindingError(
                f"Webhook call id {call_id} does not match fetched call id {snapshot.get('id')}"
            )

        developer_event = self._find_authenticated_event(call_id, event_id)
        if developer_event.get("call_id") != call_id:
            raise ProviderCallBindingError(
                "Authenticated CALL-E event call_id does not match the webhook call id"
            )

        return self._event_from_authoritative_snapshot(
            snapshot, developer_event, event_id
        )

    def _find_authenticated_event(
        self, call_id: str, event_id: str
    ) -> Dict[str, Any]:
        """Follow CALL-E cursors until the exact authenticated event is found."""
        cursor: Optional[str] = None
        seen_cursors = set()

        while True:
            try:
                page = self.get_call_events(call_id, cursor=cursor, limit=100)
            except Exception as exc:  # noqa: BLE001 - provider failures must defer safely
                logger.warning("Could not fetch CALL-E event page for %s: %s", call_id, exc)
                raise AuthoritativeSnapshotUnavailableError(
                    f"Authenticated CALL-E events unavailable for {call_id}"
                ) from exc

            if (
                not isinstance(page, dict)
                or page.get("object") != "list"
                or not isinstance(page.get("data"), list)
            ):
                raise AuthoritativeSnapshotUnavailableError(
                    f"Authenticated CALL-E event page for {call_id} was invalid"
                )

            for developer_event in page["data"]:
                if isinstance(developer_event, dict) and developer_event.get("id") == event_id:
                    return developer_event

            next_cursor = page.get("next_cursor")
            if next_cursor is None:
                raise AuthoritativeSnapshotUnavailableError(
                    f"Webhook event {event_id} was not found in authenticated CALL-E events"
                )
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                raise AuthoritativeSnapshotUnavailableError(
                    f"CALL-E event pagination for {call_id} returned an invalid cursor"
                )

            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def _event_from_authoritative_snapshot(
        self, snapshot: Dict[str, Any], developer_event: Dict[str, Any], event_id: str
    ) -> WebhookEvent:
        """Convert one authenticated CALL-E snapshot to provider-neutral terminal state."""
        status = str(snapshot.get("status") or "").strip().lower()
        terminal_statuses = {"completed", "failed", "canceled"}

        if status not in terminal_statuses:
            raise NonterminalSnapshotError(
                f"CALL-E call {snapshot.get('id')} is not terminal (status={status or 'missing'})"
            )

        if developer_event.get("id") != event_id:
            raise ProviderCallBindingError(
                "Authenticated CALL-E event id does not match the webhook event id"
            )

        authenticated_type = developer_event.get("type")
        if authenticated_type == "call.completed":
            if status != "completed":
                raise AuthoritativeSnapshotUnavailableError(
                    "Authenticated completed event conflicts with the CallTask status"
                )
            event_type = "call_completed"
        elif authenticated_type == "call.result_validation_failed":
            event_type = "result_validation_failed"
        elif authenticated_type == "call.failed":
            if status not in {"failed", "canceled"}:
                raise AuthoritativeSnapshotUnavailableError(
                    "Authenticated failed event conflicts with the CallTask status"
                )
            event_type = "call_failed"
        else:
            raise AuthoritativeSnapshotUnavailableError(
                f"Authenticated CALL-E event type is unsupported: {authenticated_type}"
            )

        metadata = snapshot.get("metadata")
        failure_code = snapshot.get("failure_code")
        failure_message = snapshot.get("failure_message")
        failure_reason = None
        if failure_code is not None or failure_message is not None:
            failure_reason = json.dumps(
                {
                    "failure_code": failure_code,
                    "failure_message": failure_message,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return WebhookEvent(
            provider_call_id=str(snapshot["id"]),
            event_type=event_type,
            structured_answers=self._extract_recipient_structured_result(snapshot),
            transcript=self._extract_transcript(snapshot),
            failure_reason=failure_reason,
            provider_event_id=event_id,
            provider_metadata=metadata if isinstance(metadata, dict) else None,
            requires_careflow_metadata=True,
        )

    def _extract_transcript(self, data: Dict[str, Any]) -> Optional[str]:
        """Best-effort transcript assembly from the first recipient's attempts."""
        recipients = data.get("recipients") or []
        if not isinstance(recipients, list) or not recipients:
            return None

        first_recipient = recipients[0]
        if not isinstance(first_recipient, dict):
            return data.get("summary")

        lines: List[str] = []
        attempts = first_recipient.get("attempts") or []
        if not isinstance(attempts, list):
            return data.get("summary")

        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            turns = attempt.get("transcript_turns") or []
            if not isinstance(turns, list):
                continue
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                speaker = turn.get("speaker", "?")
                text = turn.get("text", "")
                if text:
                    lines.append(f"{speaker}: {text}")

        return "\n".join(lines) if lines else data.get("summary")

    @staticmethod
    def _get_header_case_insensitive(headers: Dict[str, str], name: str) -> str:
        target = name.lower()
        for key, value in headers.items():
            if key.lower() == target:
                return value
        return ""

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """
        Backward-compatible envelope identity check, not a signature check.

        CALL-E currently supplies an event-ID header rather than a
        cryptographic signature. Clinical trust is established only by
        ``resolve_webhook_event`` re-fetching the call with API credentials.
        """
        try:
            self._parse_webhook_envelope(headers, raw_body)
        except InvalidWebhookEnvelopeError as exc:
            logger.warning("Webhook envelope check failed: %s", exc)
            return False

        return True

    def _parse_webhook_envelope(
        self, headers: Dict[str, str], raw_body: bytes
    ) -> tuple[str, str]:
        """Extract only event ID and call ID from inbound bytes."""
        try:
            event = json.loads(raw_body)
        except (ValueError, TypeError) as exc:
            raise InvalidWebhookEnvelopeError("Webhook body is not valid JSON") from exc

        if not isinstance(event, dict):
            raise InvalidWebhookEnvelopeError("Webhook body must be a JSON object")

        event_id_header = self._get_header_case_insensitive(headers, "CALL-E-Event-Id")
        event_id_body = event.get("id", "")
        if not event_id_header or event_id_header != event_id_body:
            raise InvalidWebhookEnvelopeError(
                "CALL-E-Event-Id header does not match the body event id"
            )

        data = event.get("data")
        if not isinstance(data, dict):
            raise InvalidWebhookEnvelopeError("Webhook data must be a JSON object")

        call_id = data.get("id")
        if not call_id:
            raise InvalidWebhookEnvelopeError("Webhook data has no call id")

        return str(event_id_body), str(call_id)
