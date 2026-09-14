# Devpost Submission Package

Finalized submission package and status record for **CALL-E: Your Code Is Calling**.
Public judge-facing links are included here; private account details such as the CALL-E account
email remain on the Devpost form and are intentionally not duplicated in this public repository.

## Final submission status

- [x] Devpost project published and submitted: https://devpost.com/software/careflow-ai-8z1p0u
- [x] Public judge demo live: https://careflowai.pythonanywhere.com
- [x] Health check live: https://careflowai.pythonanywhere.com/health
- [x] Public demo video published: https://youtu.be/zMXSo5HUZ3o
- [x] CALL-E community contribution merged upstream in [PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268)
- [x] Selected screenshots uploaded to the Devpost project gallery
- [x] CALL-E account email entered privately on the required Devpost field
- [x] CALL-E Feedback Survey submitted and additional feedback shared on Discord
- [x] Functional application frozen; this document update changes submission documentation only

## Tagline

**Explainable post-discharge follow-up that turns structured CALL-E conversations into safe,
human-reviewed care priorities.**

## The problem

Care teams cannot manually call every recently discharged patient often enough to catch every
warning sign. Pain, breathing difficulty, medication problems, fever, and worsening recovery
can go unnoticed, while staff spend time reviewing patients whose recovery is routine.

## The solution

CareFlow AI uses CALL-E to conduct a goal-driven follow-up conversation and return eight
structured recovery answers. CareFlow preserves the raw result, validates its quality, and
applies a deterministic, explainable scoring rubric only when the evidence is complete and
valid. High-risk cases create an escalation for human review; a coordinator can acknowledge it
in the dashboard. Every important transition is written to an audit timeline.

If the structured result is missing, invalid, incomplete, null, or explicitly unavailable,
CareFlow does not guess. The call becomes `needs_review`, retains the evidence for a human, and
creates no normal RiskAssessment, normal Care Summary, or clinical escalation.

## How CALL-E is meaningfully used

The real `CalleVoiceClient` sends a goal-driven task to `POST /v1/calls` with plural
`recipients`, an aggregate `result_schema`, an eight-field `recipient_result_schema`, CareFlow
correlation metadata, an optional webhook URL, and an explicit attempt-unique idempotency key.
Completed per-recipient evidence feeds the CareFlow quality, risk, escalation, summary, and
timeline workflow through a provider-independent interface.

The inbound webhook is treated as an untrusted wake-up envelope. Before any database mutation,
CareFlow cross-checks event/call identity, authenticates `GET /v1/calls/{id}` and
`GET /v1/calls/{id}/events`, binds the exact DeveloperEvent identity and type, and verifies the
fetched `reference_id` and `discharge_id`. Nonterminal/provider-fetch conditions are retryable;
tested sequential replays do not duplicate downstream artifacts. We do not claim universal
concurrent exactly-once behavior.

## What makes the approach safer and explainable

- Four-state normalization distinguishes known reassuring, known concerning, unknown/unavailable,
  and invalid/unrecognized evidence.
- The risk engine is deterministic—no opaque model decides clinical priority.
- Every score has concrete reasons and recommended action.
- Unusable evidence routes to `needs_review`, never false reassurance.
- Escalations remain visible until genuine dashboard acknowledgement.
- The application uses synthetic data only and makes no HIPAA/compliance claim.

## Product experience

- Operations dashboard with priorities, unresolved work, completed calls, and KPIs.
- Call detail with raw structured evidence, explainable risk, Care Summary, escalation,
  acknowledgement, and timeline.
- Five one-click deterministic scenarios for a reliable judge demonstration.
- Provider and notification abstractions that isolate integrations from workflow logic.
- Standalone `structured-outcome-followup-call` Agent Skill, merged into CALL-E's official
  community repository in
  [PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268).
- Public judge-facing Demo Mode at https://careflowai.pythonanywhere.com.

## Demo Mode and notification boundaries

Demo Mode uses `MockVoiceClient`; it places no real call and consumes no CALL-E credits. It
does exercise the same downstream CareFlow orchestration used after trusted real-provider
resolution.

`LogNotificationService` is the only notification implementation. CareFlow creates real
application escalation state and logs/simulates delivery behind a pluggable interface; no
external SMS, email, Slack, or paging provider is implemented. Dashboard acknowledgement is a
real state transition.

## Verification and live evidence

The final credential-free submission-hardening suite has **149 automated tests passing**, with
one pre-existing SQLAlchemy `Query.get()` `LegacyAPIWarning`. It covers provider contract
construction, authenticated webhook resolution, forged-envelope rejection,
DeveloperEvent/metadata binding, nonterminal retry, sequential replay recovery,
terminal-evidence conflict protection, normalization, result quality, risk, orchestration,
summaries, escalation, acknowledgement, Demo Mode, KPIs, health, notifications, models, and
the reusable contribution.

### Historical human validation

CareFlow's CALL-E contract was validated with genuine human conversations before the final
submission freeze.

- `call_3-bmAXd3HqzJWnK5Fg2Z6w` returned HTTP 201, reached a consenting human respondent,
  completed with `task_completed=true`, and returned all eight per-recipient recovery fields.
  Every structured value matched the spoken conversation; CALL-E completion confidence was
  high at **0.96**.
- `call_dWj5VxQM2s4lhuFsRiRm8g` returned HTTP 201 and completed with high completion confidence
  **0.95**. No numeric pain score was spoken, and CALL-E correctly returned
  `pain_level="unknown"` while preserving the other seven answers.

These calls prove real human telephony plus CALL-E structured extraction. They were controlled
provider-contract validations and are not claimed as proof of the final CareFlow webhook trust
path.

### Final frozen-build validation

On September 11, the verified frozen functional runtime successfully created a genuine CALL-E
call to the official hackathon US testing hotline. Create Call returned HTTP **201**, the
authenticated CallTask progressed from `queued` to `completed`, `task_completed=true`, and
CALL-E returned a per-recipient structured result, transcript, and matching CareFlow correlation
metadata. CALL-E task-completion confidence was high at **0.86**; this is provider completion
confidence, not a clinical-risk score.

All eight recovery answers from that hotline interaction were explicitly `unknown`. CareFlow
retrieved the genuine terminal `call.completed` DeveloperEvent, authenticated and bound the
provider state, and processed that event through the local webhook route. The result correctly
became `needs_review` with zero normal RiskAssessment, Care Summary, or Escalation artifacts.
Replaying the same genuine terminal event returned HTTP 200 and created no duplicate artifacts.

Actual public inbound webhook delivery was still not directly observed: the genuine event ID
and call ID were supplied to the local Flask webhook route, which then performed its normal
authenticated provider re-fetch and trust checks. CareFlow therefore does not claim live public
webhook delivery.

### Combined proof

The historical calls demonstrate that CALL-E genuinely reached a human and translated spoken
recovery answers into structured evidence. The frozen-build run demonstrates that the final
CareFlow runtime created a real CALL-E task and safely processed genuine provider evidence
through its authenticated trust boundary. These are complementary proofs, not duplicate claims.

A separate consenting Nigerian-destination Create Call attempt was rejected by CALL-E before
dialing with HTTP **422** `call_not_ready` because Nigeria in English was not currently
supported. No provider call ID was created. This is a provider region/language availability
boundary, not a CareFlow authentication or request-contract failure.

## Judge access

### Fastest path — hosted demo

Open https://careflowai.pythonanywhere.com, select **Run Demo Mode**, and run the **High Risk**
scenario. The public deployment is configured for deterministic mock-provider judging, so no
CALL-E account, API key, phone number, or provider credits are required and no real phone call
is placed from Demo Mode.

Health check: https://careflowai.pythonanywhere.com/health

### Local path

```bash
git clone https://github.com/macbere/careflow-ai.git
cd careflow-ai
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m app.seed
python run.py
```

Open `http://localhost:5000/dashboard` → **Open Demo Mode** → **Run High Risk**. See
`docs/JUDGE_QUICKSTART.md` for Windows activation/copy commands and evidence pointers.

## Submitted screenshot/gallery checklist

- [x] Operational dashboard
- [x] Explainable High Risk result
- [x] Human escalation acknowledgement
- [x] Generated Care Summary
- [x] Chronological audit timeline
- [x] Sanitized CALL-E contract / real-validation evidence
- [x] Official merged PR #268

## Final video checklist

- [x] Final public video published on YouTube: https://youtu.be/zMXSo5HUZ3o
- [x] Demo Mode clearly identified as deterministic/mock rather than another live call
- [x] High Risk workflow and acknowledgement shown
- [x] Historical human validation and final frozen-build validation kept distinct and truthful
- [x] Recording does not depend on another live call
- [x] Show merged community PR #268
- [x] No `.env`, API keys, phone numbers, private account details, raw payloads, or full transcripts exposed

## Owner actions — completed

- [x] OWNER ACTION: CALL-E account email added to the required Devpost field; kept private and not duplicated here
- [x] OWNER ACTION: final public video URL added and verified: https://youtu.be/zMXSo5HUZ3o
- [x] OWNER ACTION: selected screenshots uploaded to the Devpost project gallery
- [x] OWNER ACTION: public functional demo URL added: https://careflowai.pythonanywhere.com
- [x] OWNER ACTION: repository final functional state confirmed; later documentation-only status updates do not change application logic
- [x] OWNER ACTION: Devpost project published and submitted
- [x] OWNER ACTION: CALL-E Feedback Survey submitted and additional feedback shared on Discord

## Submission freeze

CareFlow AI's functional application remains frozen for the hackathon submission. Documentation
may be corrected to reflect verified submission reality, but no application-code or product-logic
change is implied by this status record.

Evidence details: [Live CALL-E Evidence](LIVE_CALLE_EVIDENCE.md).
Current boundaries: [Current Verification Status](CURRENT_VERIFICATION_STATUS.md).
