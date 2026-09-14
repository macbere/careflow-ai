# CareFlow AI submission

CareFlow is my entry for **CALL-E: Your Code Is Calling**. This page keeps the submitted links,
project description, and completion record together.

## Published links

| Item | Link |
|---|---|
| Devpost project | [CareFlow AI](https://devpost.com/software/careflow-ai-8z1p0u) |
| Live demo | [CareFlow dashboard](https://careflowai.pythonanywhere.com) |
| Health check | [Service health](https://careflowai.pythonanywhere.com/health) |
| Demo video | [Watch on YouTube](https://youtu.be/zMXSo5HUZ3o) |
| Community contribution | [Merged CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268) |

## Tagline

Post-discharge follow-up that turns CALL-E conversations into clear priorities for human review.

## The problem and approach

Following up after discharge involves more than placing a call. Someone needs to review the
answers, identify concerns, and keep track of what happened next. CareFlow brings those steps
into one workflow.

CALL-E asks eight recovery questions and returns structured answers. CareFlow stores the raw
result, checks that it is complete and valid, and applies a rule-based scoring rubric. Each
score includes reasons. High-risk results create an escalation that a coordinator can
acknowledge in the dashboard.

An incomplete or unusable result becomes `needs_review`. Missing, invalid, null, or explicitly
unknown answers create no normal RiskAssessment, Care Summary, or clinical escalation. They
remain available for a person to review.

## How CALL-E fits

The real `CalleVoiceClient` creates a goal-driven task with plural `recipients`, aggregate and
per-recipient result schemas, CareFlow correlation metadata, an optional callback URL, and an
attempt-unique idempotency key.

Before processing a webhook result, CareFlow retrieves the call and its DeveloperEvents through
authenticated requests. It checks the event identity/type and matches the fetched
`reference_id` and `discharge_id` to local records. Provider-fetch failures and nonterminal
state are retryable. Sequential replay tests cover duplicate handling; the implementation does
not guarantee concurrent exactly-once processing.

The [architecture](ARCHITECTURE.md) has the request fields and processing details.

## Product walkthrough

The dashboard shows follow-up priorities, pending work, unresolved escalations, completed calls,
and KPIs. Call detail brings together structured answers, score and reasons, Care Summary,
acknowledgement, and the audit timeline.

For a quick tour, open the live demo, choose **Run Demo Mode**, and run **High Risk**. There are
also Healthy Recovery, Moderate Concern, Failed Call, and No Answer scenarios. The
[judge quick-start](JUDGE_QUICKSTART.md) includes local setup instructions.

Demo Mode uses `MockVoiceClient`: it places no real call and requires no API key or credits.
Notification delivery is logged through `LogNotificationService`; no external SMS, email,
Slack, or paging provider is connected. Escalations and acknowledgements are stored application
state.

## Validation

The submission suite has **149 passing automated tests**, with one existing SQLAlchemy
`Query.get()` `LegacyAPIWarning`. Coverage includes provider requests, authenticated webhook
resolution, forged-envelope rejection, metadata binding, retries, replay recovery, conflicting
evidence, result quality, scoring, summaries, escalation, acknowledgement, Demo Mode, KPIs,
health, models, notifications, and the reusable contribution.

Earlier controlled CALL-E calls reached a consenting human and extracted recovery answers,
including an explicit unknown pain score. On September 11, the submission build created a real
task to the official test hotline, verified its returned provider data, and routed eight
unknown answers to `needs_review`. Replaying the same event produced no duplicate records.

That application test used the local webhook route. Public inbound webhook delivery was not
observed. A separate Nigerian-destination call attempt was rejected before dialing with
HTTP 422 `call_not_ready`; CALL-E reported Nigeria in English as unsupported at the time.
The [live evidence record](LIVE_CALLE_EVIDENCE.md) contains the full results.

## Community contribution

The `structured-outcome-followup-call` Agent Skill generalizes the workflow into a standalone,
non-healthcare example. It is dependency-free and includes tests. CALL-E merged it in
[PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268); a copy is retained in
`calle-contrib/`.

## Submission record

- Devpost project published and submitted, with the public demo and video links.
- Gallery uploaded: dashboard, High Risk result, acknowledgement, Care Summary, timeline,
  sanitized validation evidence, and the merged community contribution.
- CALL-E account email entered privately in the required Devpost field.
- CALL-E Feedback Survey submitted, with additional feedback shared on Discord.
- Video checklist completed: mock demonstration identified, human-call and application-test
  evidence distinguished, and PR #268 shown. Credentials, phone numbers, private account
  details, raw payloads, and full transcripts were excluded.

The submission's application behavior remains frozen. Documentation and comment edits do not
change product logic. CareFlow uses synthetic data only, is not HIPAA-reviewed, and makes no
production or compliance claim. See [verification status](CURRENT_VERIFICATION_STATUS.md).

Project Owner: Macdonald ([macbere](https://github.com/macbere)). I lead the product direction
and review, with AI assistance for implementation and documentation.
