# Devpost Submission Package

Paste-ready draft for **CALL-E: Your Code Is Calling**. Owner-supplied links and account
details remain explicitly marked; no values are invented here.

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

On September 11, the verified frozen functional runtime successfully created
a genuine CALL-E call to the official hackathon US testing hotline. Create Call returned HTTP
**201**, the authenticated CallTask progressed from `queued` to `completed`,
`task_completed=true`, and CALL-E returned a per-recipient structured result, transcript, and
matching CareFlow correlation metadata. CALL-E task-completion confidence was high at **0.86**;
this is provider completion confidence, not a clinical-risk score.

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

## How to run

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

## Screenshot checklist

- [ ] Dashboard with operational priorities and five KPI cards
- [ ] Demo Mode scenario picker, visibly labeled simulated/mock
- [ ] High Risk call detail with reasons and recommended action
- [ ] Escalation and acknowledgement controls
- [ ] Care Summary and audit timeline
- [ ] `needs_review` example showing no normal clinical artifacts
- [ ] Sanitized two-layer live-evidence view with no phone numbers or private account data
- [ ] Official merged PR #268

## Video checklist

- [ ] Under 3:00; target 2:40–2:50
- [ ] Clearly label Demo Mode as `MockVoiceClient`, not a live call
- [ ] Show High Risk workflow and acknowledgement
- [ ] Briefly show historical human validation as proof of real CALL-E conversation + structured extraction
- [ ] Show the final frozen-build proof: HTTP 201 Create Call, completed CallTask, authenticated terminal event, metadata binding, safe `needs_review` routing, and no duplicate replay artifacts
- [ ] Keep the two validation layers distinct and truthful
- [ ] Do not make the recording depend on another live call
- [ ] Show merged community PR #268
- [ ] Do not expose `.env`, API keys, phone numbers, private account details, raw payloads, or full transcripts

## OWNER ACTIONS before submission

- [ ] OWNER ACTION: add the CALL-E account email required by the event form
- [ ] OWNER ACTION: add and privately verify the final public video URL
- [ ] OWNER ACTION: upload the selected screenshots
- [ ] OWNER ACTION: add an optional deployment URL only if a safe public demo is available
- [ ] OWNER ACTION: confirm the repository branch/commit submitted is the approved final state

Evidence details: [Live CALL-E Evidence](LIVE_CALLE_EVIDENCE.md).
Current boundaries: [Current Verification Status](CURRENT_VERIFICATION_STATUS.md).
