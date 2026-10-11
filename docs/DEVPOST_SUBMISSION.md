# CareFlow AI submission

CareFlow AI is my entry for **CALL-E: Your Code Is Calling**. This document records the final
submitted links, project description, validation evidence, and completed submission actions.

> **Status:** Submitted and frozen. Product/application logic is frozen; documentation-only
> updates do not change application behavior.

## Published links

| Item | Link |
|---|---|
| Devpost project | [CareFlow AI](https://devpost.com/software/careflow-ai-8z1p0u) |
| Live judge demo | [CareFlow dashboard](https://careflowai.pythonanywhere.com) |
| Health check | [Service health](https://careflowai.pythonanywhere.com/health) |
| Demo video | [Watch on YouTube](https://youtu.be/zMXSo5HUZ3o) |
| Community contribution | [Merged CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268) |
| Source repository | [macbere/careflow-ai](https://github.com/macbere/careflow-ai) |

## Final Devpost tagline

**CareFlow AI uses CALL-E to turn post-discharge follow-up calls into explainable risk priorities
and human escalation.**

## The problem and approach

Following up after discharge involves more than placing a call. Someone needs to review the
answers, identify concerns, and keep track of what happened next. CareFlow AI brings those steps
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
not claim universal concurrent exactly-once processing.

The [architecture](ARCHITECTURE.md) documents the request fields and processing details.

## Product walkthrough

The dashboard shows follow-up priorities, pending work, unresolved escalations, completed calls,
and KPIs. Call detail brings together structured answers, score and reasons, Care Summary,
acknowledgement, and the audit timeline.

For the fastest judge path, open the
[live demo](https://careflowai.pythonanywhere.com), select **Run Demo Mode**, and run
**High Risk**. There are also Healthy Recovery, Moderate Concern, Failed Call, and No Answer
scenarios. The [judge quick-start](JUDGE_QUICKSTART.md) includes local setup instructions.

Demo Mode uses `MockVoiceClient`: it places no real call and requires no API key or CALL-E
credits. Notification delivery is logged through `LogNotificationService`; no external SMS,
email, Slack, or paging provider is connected. Escalations and acknowledgements are stored
application state.

## Validation

The submission suite has **149 passing automated tests**, with one existing SQLAlchemy
`Query.get()` `LegacyAPIWarning`. Coverage includes provider requests, authenticated webhook
resolution, forged-envelope rejection, metadata binding, retries, replay recovery, conflicting
evidence, result quality, scoring, summaries, escalation, acknowledgement, Demo Mode, KPIs,
health, models, notifications, and the reusable contribution.

Earlier controlled CALL-E calls reached a consenting human and extracted recovery answers,
including an explicit unknown pain score. On September 11, the frozen submission build created
a real task to the official hackathon testing route, verified its returned provider data, and
routed eight unknown answers to `needs_review`. Replaying the same genuine terminal event
created no duplicate downstream records.

That frozen-build validation used the local webhook route to initiate processing from the
genuine provider event/call identifiers, followed by CareFlow's normal authenticated provider
re-fetch. Public inbound webhook delivery was not directly observed.

A separate Nigerian-destination call attempt was rejected before dialing with HTTP 422
`call_not_ready`; CALL-E reported Nigeria in English as unsupported at the time.

The [live evidence record](LIVE_CALLE_EVIDENCE.md) contains the full evidence matrix and truth
boundaries.

## Community contribution

The `structured-outcome-followup-call` Agent Skill generalizes the workflow into a standalone,
non-healthcare example. It is dependency-free and includes tests.

CALL-E **merged** it in
[PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268) on August 31, 2026.
Merge commit: `631e105be1a25822672c97d31b1557be809d1eec`.

A copy is retained in `calle-contrib/`.

## Final screenshot/gallery checklist

The final Devpost gallery uses the selected judge-facing evidence rather than every early
planning screenshot.

- [x] Operational dashboard
- [x] Explainable High Risk result
- [x] Human acknowledgement
- [x] Generated Care Summary
- [x] Chronological audit timeline
- [x] Sanitized CALL-E contract / real-validation evidence
- [x] Official merged PR #268

## Final video checklist

- [x] Public YouTube demo video added to Devpost
- [x] Demo Mode clearly presented as deterministic/mock rather than a live phone call
- [x] High Risk workflow and acknowledgement demonstrated
- [x] Historical human validation and frozen-build validation kept distinct
- [x] Real CALL-E evidence presented without overstating public webhook delivery
- [x] Video does not depend on placing another live call
- [x] Show merged community PR #268
- [x] No API keys, phone numbers, private account details, raw payloads, or full private transcripts exposed

Final public video:
[https://youtu.be/zMXSo5HUZ3o](https://youtu.be/zMXSo5HUZ3o)

## Completed owner actions

- [x] CALL-E account email entered privately in the required Devpost field
- [x] Final public video URL added and verified
- [x] Selected submission screenshots uploaded
- [x] Public functional demo URL added: [https://careflowai.pythonanywhere.com](https://careflowai.pythonanywhere.com)
- [x] Repository/source link included
- [x] Approved final repository state confirmed for submission
- [x] CALL-E PR URL supplied in the Devpost submission
- [x] CALL-E Feedback Survey submitted
- [x] Additional CALL-E feedback shared on Discord
- [x] Devpost project published and submitted

## Final submission record

- Devpost project: **published and submitted**
- Live judge demo: **online at `careflowai.pythonanywhere.com`**
- Demo video: **public on YouTube**
- Gallery: **uploaded**
- CALL-E community contribution: **PR #268 merged**
- Automated suite: **149 passing tests**
- Functional application behavior: **frozen**
- Public documentation: may receive truth-preserving status/comment updates only; no product
  logic changes are implied by such documentation edits

CareFlow AI uses synthetic data only, is not HIPAA-reviewed, and makes no production,
regulatory, or compliance claim.

See [Current Verification Status](CURRENT_VERIFICATION_STATUS.md),
[Live CALL-E Evidence](LIVE_CALLE_EVIDENCE.md), and
[Judge Quick-Start](JUDGE_QUICKSTART.md).

Project Owner: Macdonald ([macbere](https://github.com/macbere)).
