"""
Abstract voice-provider interface.

Every concrete voice provider (CALL-E, a mock for local dev, or a future
alternative provider) implements this interface. Nothing outside the
`app/services/calle/` package and `call_orchestrator.py` should ever import
a concrete client directly — always depend on this abstraction so swapping
providers is a one-file change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecoveryQuestion:
    """One structured question the voice agent should ask during the call."""

    key: str  # machine-readable key, e.g. "pain_level"
    prompt: str  # what the agent should ask the patient


@dataclass
class CallRequest:
    """Everything a voice provider needs to place a follow-up call."""

    patient_name: str
    phone_number: str
    discharge_diagnosis: str
    questions: List[RecoveryQuestion]
    # Local reference ID (our FollowUpCall.id) so we can correlate the
    # provider's webhook/response back to the right row before we know the
    # provider's own call ID.
    reference_id: str
    # Stable identity for retrying this exact logical call attempt. Real
    # providers may require it; mock/demo callers can leave it unset.
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallInitiationResult:
    """Result of successfully asking the provider to place a call."""

    provider_call_id: str
    status: str  # e.g. "initiated", "queued"


class VoiceProviderClient(ABC):
    """Abstract base class every voice provider client must implement."""

    @abstractmethod
    def initiate_call(self, call_request: CallRequest) -> CallInitiationResult:
        """
        Ask the provider to place an outbound call.

        Must not block waiting for the call to complete — voice calls are
        asynchronous; completion is reported later via `parse_webhook_event`.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_webhook_event(self, raw_payload: Dict[str, Any]) -> "WebhookEvent":
        """
        Normalize a provider-specific webhook payload into our internal
        WebhookEvent shape, so the orchestrator never has to know the
        provider's wire format.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_webhook_event(
        self, headers: Dict[str, str], raw_body: bytes
    ) -> "WebhookEvent":
        """
        Resolve an untrusted webhook envelope into a trusted internal event.

        Real providers must re-fetch authoritative state before returning.
        Mock providers may parse their locally generated payload directly.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """Backward-compatible envelope check; not the clinical trust boundary."""
        raise NotImplementedError


class WebhookResolutionError(ValueError):
    """Base class for failures while resolving an untrusted webhook."""


class InvalidWebhookEnvelopeError(WebhookResolutionError):
    """The inbound envelope is malformed or fails its documented ID check."""


class AuthoritativeSnapshotUnavailableError(WebhookResolutionError):
    """The provider's authoritative call snapshot could not be fetched."""


class NonterminalSnapshotError(WebhookResolutionError):
    """The authoritative provider snapshot is not terminal yet."""


class ProviderCallBindingError(WebhookResolutionError):
    """Provider identifiers or returned metadata do not bind to the local call."""


class TerminalEvidenceConflictError(WebhookResolutionError):
    """A replay conflicts with evidence that has already been assessed."""


@dataclass
class WebhookEvent:
    """Normalized representation of a call-completed (or failed) webhook."""

    provider_call_id: str
    # "call_completed" | "result_validation_failed" | "call_failed" | "no_answer"
    event_type: str
    structured_answers: Optional[Dict[str, Any]] = None
    transcript: Optional[str] = None
    failure_reason: Optional[str] = None
    provider_event_id: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None
    requires_careflow_metadata: bool = False
