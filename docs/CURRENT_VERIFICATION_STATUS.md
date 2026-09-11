# Current Verification Status

This is the authoritative current-state summary for CareFlow AI. Earlier internal engineering
records are not part of the submission-facing repository; this document is the canonical source
for the final verification state and evidence boundaries.

| Item | Current state |
|---|---|
| Project | CareFlow AI |
| Hackathon | CALL-E — Your Code Is Calling |
| Functional code freeze | Verified; 149-test functional suite passed |
| Functional suite before submission hardening | 149 passed |
| Submission-hardening suite | **149 passed** |
| Known warning | One pre-existing SQLAlchemy `Query.get()` `LegacyAPIWarning` |
| Final live-validation runtime | Verified against genuine CALL-E provider evidence |
| Functional code state | **FROZEN** |

## Two-layer CALL-E evidence

CareFlow's real-provider evidence is intentionally separated into two complementary layers.
This avoids overstating what any one validation run proved.

### Layer 1 — historical human validation

Earlier controlled CALL-E validations reached a consenting human respondent and exercised the
structured-answer contract directly.

#### Complete eight-answer call

Provider call ID: `call_3-bmAXd3HqzJWnK5Fg2Z6w`

- Create Call returned HTTP **201**.
- The call reached a human respondent and completed.
- `status="completed"`, `task_completed=true`.
- Completion confidence: **high / 0.96**.
- All eight per-recipient recovery fields were returned.
- Every structured field matched what was spoken in the preserved transcript.
- No CALL-E failure code or failure message was present.

#### Explicit-unknown call

Provider call ID: `call_dWj5VxQM2s4lhuFsRiRm8g`

- Create Call returned HTTP **201**.
- The call reached a human respondent and completed.
- `status="completed"`, `task_completed=true`.
- Completion confidence: **high / 0.95**.
- No numeric pain score was spoken.
- CALL-E returned `pain_level="unknown"` rather than fabricating a number.
- The other seven fields matched the spoken answers.

These historical calls prove real human telephony and structured extraction. They were
controlled provider-contract validations; they are not presented as proof of the final
CareFlow webhook trust path.

### Layer 2 — September 11 final frozen-build validation

On the verified frozen functional runtime, CareFlow made exactly one
genuine Create Call to CALL-E's official hackathon US testing hotline.

- `POST /v1/calls` returned HTTP **201**, a provider call ID was created, and the authenticated
  CallTask progressed from `queued` to `completed`.
- CALL-E reported `task_completed=true` with completion confidence **high / 0.86**. This is
  provider task-completion confidence, not a clinical-risk score.
- Returned `reference_id` and `discharge_id` metadata matched the local CareFlow call and
  discharge records.
- A per-recipient structured result and transcript were present. All eight recovery fields were
  explicitly `unknown`.
- CareFlow retrieved authenticated DeveloperEvents, found a bound terminal `call.completed`
  event, and exercised the local webhook route using only that genuine event ID and call ID as
  the inbound envelope.
- The webhook route returned HTTP **200** after re-fetching authoritative provider state.
  Because every clinical answer was explicitly unknown, CareFlow routed the call and discharge
  to `needs_review`, created **zero** normal RiskAssessments, Care Summaries, and Escalations,
  and created exactly **one** review timeline event.
- Replaying the same genuine terminal event returned HTTP **200** and created no duplicate
  downstream artifacts.

This validates real CALL-E creation, authenticated terminal-state retrieval, metadata binding,
uncertainty handling, and sequential replay behavior in the final frozen runtime. It does
**not** prove that CALL-E delivered a webhook to a public CareFlow URL, because the inbound
envelope was initiated locally and the route then performed its normal authenticated provider
re-fetch.

### Combined interpretation

The historical human calls prove that CALL-E genuinely reached a person and converted spoken
recovery answers into structured evidence. The frozen-build run proves that the final CareFlow
runtime created a real CALL-E task and safely processed genuine provider evidence through its
authenticated trust boundary. Together they cover the two most important real-world sides of
the submission without conflating their verification scopes.

Full evidence matrix: [Live CALL-E Evidence](LIVE_CALLE_EVIDENCE.md).

## Nigerian-destination live validation

- Using the final live-validation runtime and a valid credential, CareFlow made exactly one
  Create Call attempt to a consenting Nigerian test destination.
- CALL-E rejected task creation before dialing with HTTP **422** and error code
  `call_not_ready`, stating that calling Nigeria in English was not currently supported.
- No provider call ID was created and no Nigerian phone call occurred.
- This is recorded as a provider region/language availability boundary, not a CareFlow
  authentication, request-schema, metadata, or idempotency failure. No retry was made.

## Public-webhook boundary

- Actual public inbound webhook delivery has **not** been directly observed.
- The real webhook handler treats the inbound body as an untrusted wake-up envelope. It binds
  the event ID and call ID to authenticated `GET /v1/calls/{id}` and
  `GET /v1/calls/{id}/events` results, verifies exact DeveloperEvent identity/type, and binds
  CareFlow `reference_id` and `discharge_id` metadata before orchestration.
- The September 11 frozen-build validation exercised that trust path locally using a genuine
  terminal provider event. Forged-body, binding, nonterminal, provider-failure, data-quality,
  terminal-conflict, and sequential-replay behavior remain covered by automated tests.

## Demo, notification, and production boundaries

- **Demo Mode:** deterministic `MockVoiceClient`; consumes no CALL-E credits; exercises the
  downstream CareFlow orchestration; is not a real phone call.
- **Notifications:** `LogNotificationService` is the only implementation. Escalation creation
  and dashboard acknowledgement are real application-state transitions; external SMS, email,
  Slack, or paging delivery is not implemented.
- **Clinical safety:** incomplete, invalid, missing, or explicitly unavailable structured
  evidence becomes `needs_review`; it does not create a normal `RiskAssessment`, normal Care
  Summary, or clinical escalation.
- **Data/compliance:** synthetic data only; not HIPAA-reviewed; no production authentication,
  RBAC, tenancy, EHR, or compliance claim.
- **Idempotency:** repeated terminal processing is protected for the tested sequential/retry
  paths. The project does not claim universal concurrent exactly-once processing.

## Repository-facing privacy boundary

Recipient phone numbers, credentials, private account details, and raw call transcripts are not
included in the judge-facing documentation. Evidence is summarized at the provider-result and
workflow level instead.
