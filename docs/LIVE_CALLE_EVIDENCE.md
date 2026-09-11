# Live CALL-E Evidence

This document separates CareFlow's real-provider evidence into two complementary layers. The
goal is to show exactly what was verified without making one experiment stand in for another.

No recipient phone numbers, credentials, raw transcripts, or private account details are
included here.

## Evidence matrix

| Evidence layer | What happened | What it proves | What it does not prove |
|---|---|---|---|
| Historical human validation | CALL-E reached a consenting human respondent, asked the recovery questions, and returned structured results that matched the conversation | Real telephony, human conversation handling, per-recipient structured extraction, explicit uncertainty preservation | The final CareFlow webhook trust path |
| Final frozen-build validation | The frozen CareFlow runtime created a genuine CALL-E task to the official hackathon hotline and processed genuine terminal provider evidence through its authenticated resolver | Real Create Call, authenticated CallTask/Event retrieval, metadata binding, `needs_review` safety routing, sequential replay protection | Public inbound webhook delivery |
| Demo Mode | Deterministic `MockVoiceClient` scenarios exercise downstream CareFlow workflow | Reliable judge-facing product demonstration | A live phone call |

## Layer 1 — historical human validation

### Complete eight-answer call

Provider call ID: `call_3-bmAXd3HqzJWnK5Fg2Z6w`

- `POST /v1/calls` returned HTTP **201**.
- The call reached a consenting human respondent and ran through a full conversation.
- Final CALL-E status: `completed`.
- `task_completed=true`.
- Completion confidence: **high / 0.96**.
- `recipients[0].structured_result` contained all eight requested recovery fields.
- Each structured value matched what the human actually said in the preserved transcript.
- CALL-E reported no failure code or failure message.

This is the strongest historical proof that CALL-E genuinely performed the recovery interview
with a human and converted the spoken responses into structured per-recipient evidence.

### Explicit-unknown call

Provider call ID: `call_dWj5VxQM2s4lhuFsRiRm8g`

- `POST /v1/calls` returned HTTP **201**.
- The call reached a consenting human respondent and completed.
- Final CALL-E status: `completed`.
- `task_completed=true`.
- Completion confidence: **high / 0.95**.
- The respondent deliberately did not provide a numeric pain score.
- CALL-E returned `pain_level="unknown"` rather than fabricating a number.
- The other seven recovery fields were present and matched the spoken answers.

This call is important because it verifies uncertainty preservation at the provider contract:
ambiguous numeric evidence was represented explicitly instead of being silently converted into
reassuring data.

### Historical-validation boundary

These historical calls were controlled CALL-E provider-contract validations. They prove real
human telephony and structured-result behavior. They are not presented as evidence that the
final CareFlow webhook resolver or full frozen runtime processed those exact calls end-to-end.

## Layer 2 — final frozen-build validation

Verified frozen functional runtime: September 11 submission build.

On September 11, this frozen runtime created a genuine CALL-E call to the official hackathon US
testing hotline.

### Provider evidence

- Exactly one Create Call POST was issued.
- `POST /v1/calls` returned HTTP **201**.
- A real provider call ID was created.
- Authenticated CallTask state progressed from `queued` to `completed`.
- `task_completed=true`.
- CALL-E task-completion confidence: **high / 0.86**.
- Returned CareFlow `reference_id` and `discharge_id` metadata matched the local records.
- A transcript and per-recipient structured result were present.
- All eight recovery fields were explicit `unknown` values because the official hotline did not
  provide usable patient answers.
- Authenticated DeveloperEvent retrieval returned a bound terminal `call.completed` event.

The 0.86 value is CALL-E task-completion confidence, not a clinical-risk score.

### CareFlow processing evidence

CareFlow exercised its local webhook route using only the genuine provider event ID and call ID
as the inbound envelope. The handler then followed the normal trust path:

```text
untrusted event/call envelope
  -> authenticated GET /v1/calls/{id}
  -> authenticated GET /v1/calls/{id}/events
  -> exact DeveloperEvent identity/type binding
  -> reference_id + discharge_id binding
  -> result-quality gate
  -> CareFlow workflow
```

Observed result:

- Local webhook route returned HTTP **200**.
- `FollowUpCall` became `needs_review`.
- `Discharge` became `needs_review`.
- Normal RiskAssessment count: **0**.
- Normal Care Summary count: **0**.
- Clinical Escalation count: **0**.
- Review timeline count: **1**.
- Replaying the same genuine terminal event returned HTTP **200**.
- Artifact counts were unchanged after replay; no duplicates were created.

### Frozen-build boundary

Public inbound webhook delivery was not directly observed. The genuine event envelope was
initiated locally; the route then authenticated provider state and DeveloperEvents exactly as it
would for an inbound notification. CareFlow therefore claims verified trust-path processing,
not verified public webhook delivery.

## Combined interpretation

The two evidence layers answer different questions:

1. **Can CALL-E genuinely call a human and capture recovery answers accurately?** Yes — the
   historical human validation demonstrates this directly.
2. **Can the final CareFlow runtime create a real CALL-E task and safely process genuine provider
   evidence?** Yes — the frozen-build validation demonstrates real creation, authenticated
   resolution, metadata binding, uncertainty routing, and replay protection.
3. **Can judges evaluate the product without depending on live telephony?** Yes — Demo Mode
   provides deterministic downstream scenarios while remaining explicitly labeled as mock.

Together, these layers provide stronger evidence than either one alone while preserving the
truth boundary of each experiment.

## Additional provider boundary

A separate consenting Nigerian-destination Create Call attempt was rejected before dialing with
HTTP **422** `call_not_ready`, with CALL-E stating that Nigeria in English was not currently
supported. No provider call ID was created. This is recorded as provider region/language
availability, not as a CareFlow request-contract or authentication failure.

## Related documents

- [Current Verification Status](CURRENT_VERIFICATION_STATUS.md)
- [Architecture](ARCHITECTURE.md)
- [Demo Recording Plan](DEMO_RECORDING_PLAN.md)
- [Devpost Submission Package](DEVPOST_SUBMISSION.md)
