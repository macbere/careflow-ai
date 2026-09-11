# Architecture

## System view

```mermaid
flowchart TB
    UI[Dashboard and Demo Mode] --> API[Flask API routes]
    API --> ORCH[CallOrchestrator]
    ORCH --> VOICE[VoiceProviderClient]
    VOICE -. real .-> CALLE[CalleVoiceClient]
    VOICE -. demo/test .-> MOCK[MockVoiceClient]
    CALLE <--> PLATFORM[CALL-E REST API]
    API --> TRUST[Authenticated webhook resolution]
    TRUST --> PLATFORM
    TRUST --> ORCH
    ORCH --> QUALITY[ResultQuality safety gate]
    QUALITY -->|valid + complete| RISK[Deterministic Risk Engine]
    QUALITY -->|missing / invalid / unknown| REVIEW[needs_review]
    RISK --> ESC[Escalation Service]
    ESC --> NOTIFY[NotificationService]
    NOTIFY -. current .-> LOG[LogNotificationService]
    RISK --> SUMMARY[Care Summary]
    ORCH --> DATA[(SQLAlchemy models)]
    RISK --> DATA
    ESC --> DATA
    SUMMARY --> DATA
    UI --> DATA
```

The application layer depends on the abstract `VoiceProviderClient`; the provider factory is
the single selection point for real CALL-E versus the deterministic mock. The same abstraction
exists for notifications, although only log-based delivery is implemented today.

## Outbound call initiation

```text
Discharge created
  -> CallOrchestrator creates and flushes FollowUpCall
  -> attempt-unique, stable, non-sensitive idempotency key generated
  -> CalleVoiceClient POST /v1/calls
       task
       recipients: [{phones: [...]}]
       result_schema: aggregate completion count
       recipient_result_schema: eight recovery answers
       metadata: reference_id + discharge_id
       optional webhook_url
  -> provider_call_id stored
```

The mock provider follows the same interface but does not make a network request.

## Real inbound webhook trust boundary

The real HTTP route does **not** pass webhook-body clinical fields directly to
`process_webhook_event(raw_payload)`. The body is an untrusted wake-up envelope:

```text
POST /api/webhooks/calle
  -> cross-check CALL-E-Event-Id header, body event ID, and body call ID
  -> authenticated GET /v1/calls/{call_id}
  -> authenticated GET /v1/calls/{call_id}/events (cursor-aware)
  -> find and bind the exact DeveloperEvent ID, call ID, and terminal type
  -> bind fetched CallTask ID
  -> bind CareFlow metadata reference_id + discharge_id
  -> create a trusted provider-neutral WebhookEvent
  -> CallOrchestrator.process_event(event)
```

Failure behavior is deliberate:

- malformed/mismatched envelope → HTTP 401
- nonterminal authenticated state → retryable HTTP 503
- provider call/event fetch unavailable or event not yet visible → retryable HTTP 503
- provider/CareFlow identity mismatch or conflicting terminal evidence → HTTP 409
- no database mutation occurs before resolution succeeds

`CALLE_WEBHOOK_SECRET` is not part of this trust boundary. It is an unused forward-compatible
configuration surface, not an HMAC/shared-secret requirement.

## Result-quality and clinical workflow

```text
trusted terminal event
  -> result_validation_failed -> needs_review
  -> completed result -> four-state normalization / ResultQuality
       valid and complete
         -> store completed evidence
         -> RiskAssessment
         -> optional high-risk EscalationEvent
         -> LogNotificationService records simulated delivery
         -> normal CareSummary
       incomplete, invalid, missing, null, or explicit unknown
         -> preserve raw evidence
         -> status = needs_review
         -> human-review timeline event
         -> NO RiskAssessment
         -> NO normal CareSummary
         -> NO clinical escalation
  -> failed/no-answer -> terminal noncompletion state; no clinical assessment
```

An acknowledged escalation is a genuine application-state transition and timeline event. It
does not imply an external nurse messaging service exists.

## Replay behavior

Processing uses existing artifacts plus `log_event_once()` to resume a partially completed
terminal workflow. Repeated equivalent events do not duplicate risk assessments, summaries,
escalations, or timeline effects in the tested sequential/retry paths. Conflicting answers
after assessment are rejected rather than overwriting clinical evidence. This design does not
claim universal concurrent exactly-once processing.

## Data model

```text
Patient 1---* Discharge 1---* FollowUpCall 1---0..1 RiskAssessment 1---0..1 EscalationEvent
                                   |
                                   +---0..1 CareSummary

TimelineEvent has nullable patient/discharge/call references for auditable workflow history.
```
