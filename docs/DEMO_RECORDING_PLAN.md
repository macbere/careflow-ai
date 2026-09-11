# CareFlow AI — Final Demo Recording Plan

**Hackathon:** CALL-E — Your Code Is Calling

**Absolute limit:** under 3:00

**Target:** 2:40–2:50

## Truthfulness rule

Demo Mode uses the deterministic `MockVoiceClient`. It simulates a provider outcome, places no
real phone call, and consumes no CALL-E credits.

Real-provider proof is shown separately in two layers:

1. **Historical human validation:** CALL-E genuinely reached a consenting human respondent and
   captured spoken recovery answers into per-recipient structured results. One completed call
   returned all eight answers correctly; another preserved an unavailable numeric pain answer
   as `pain_level="unknown"` rather than inventing a value.
2. **Final frozen-build validation:** the verified frozen functional runtime successfully created and completed a genuine
   CALL-E call to the official hackathon US testing hotline. CareFlow authenticated terminal
   provider state and the bound DeveloperEvent, verified correlation metadata, and routed the
   all-`unknown` result to `needs_review` without creating normal clinical artifacts.

The recording should **not** place another live call. Use Demo Mode for the deterministic
product walkthrough and the evidence documents for real-provider proof.

Do not display `.env`, API keys, phone numbers, private account details, raw recipient payloads,
or full transcripts. Provider call/event IDs are not needed on screen.

## Recording sequence

| Time | Screen | Action |
|---|---|---|
| 0:00–0:18 | Dashboard | State the post-discharge follow-up problem and CareFlow's purpose. |
| 0:18–0:42 | Dashboard | Show operational priorities and five KPIs. |
| 0:42–1:24 | Demo Mode → High Risk | Run the deterministic mock scenario; show evidence, explainable score, reasons, and escalation. |
| 1:24–1:50 | Call detail | Show Care Summary, logged notification state, acknowledgement, and timeline. |
| 1:50–2:05 | `docs/LIVE_CALLE_EVIDENCE.md` | Show the historical human-validation row and explain that CALL-E genuinely called a person and captured structured answers. |
| 2:05–2:27 | `docs/LIVE_CALLE_EVIDENCE.md` / architecture | Show the frozen-build evidence and authenticated trust flow; explain the `needs_review` outcome. |
| 2:27–2:39 | GitHub | Show official merged CALL-E PR #268. |
| 2:39–2:50 | Dashboard | Close on human prioritization and uncertainty preservation. |

## Suggested narration

### 0:00–0:18 — Problem

“Care teams cannot manually call every discharged patient often enough to catch every warning
sign. CareFlow turns follow-up conversations into structured evidence and surfaces the patients
who need human attention.”

### 0:18–0:42 — Operations view

“The dashboard puts elevated risk, unresolved follow-ups, and acknowledgement state in one
place, so a coordinator starts with priorities rather than every raw call.”

### 0:42–1:24 — High Risk Demo Mode

“This deterministic demo uses CareFlow's `MockVoiceClient`; it is not placing a phone call. The
mock emits the same provider-neutral outcome consumed downstream by the real integration.
CareFlow validates the evidence, explains the risk score, and creates an escalation.”

### 1:24–1:50 — Human loop

“CareFlow records notification delivery through its current log-based adapter; it does not yet
send SMS, email, or Slack. The coordinator's acknowledgement is a real application-state
transition, and the summary and timeline preserve what happened.”

### 1:50–2:05 — Historical human validation

“CALL-E was also validated with a real human respondent. In one completed call, all eight
recovery answers were captured correctly from the spoken conversation. In a separate
uncertainty test, no numeric pain score was given, and CALL-E preserved that value as unknown
instead of inventing a number.”

Optional: use a **5–7 second audio-only excerpt** from a consenting historical validation call
while keeping phone numbers, call IDs, and the full transcript off screen. The excerpt is
supporting proof, not the primary product demonstration.

### 2:05–2:27 — Final frozen-build validation

“On the frozen functional build, CareFlow then created a genuine CALL-E task through the
official hackathon testing route. The call completed, CareFlow authenticated the returned call
and terminal event, verified its metadata binding, and safely routed unusable recovery evidence
to human review instead of guessing. Replaying the same terminal event created no duplicate
artifacts.”

Show `docs/LIVE_CALLE_EVIDENCE.md`, `docs/ARCHITECTURE.md`, or the relevant trust-flow code.
Do not claim public inbound webhook delivery; the final validation used a genuine provider event
through the local webhook route, which then re-fetched authenticated provider state.

### 2:27–2:39 — Community contribution

“We generalized the structured-outcome pattern into a reusable Agent Skill, and CALL-E merged
it into the official community repository as pull request 268.”

### 2:39–2:50 — Close

“CareFlow turns phone follow-up into actionable, explainable care priorities while keeping
uncertain evidence in human hands.”

## Recording rules

1. Keep the final export below 3:00; target 2:40–2:50.
2. Keep High Risk Demo Mode as the primary product demonstration.
3. Clearly label Demo Mode as mock/simulated provider outcome.
4. Present historical human validation and final frozen-build validation as separate evidence
   layers; do not imply the historical contract tests exercised the final trust path.
5. Do not place another live call during recording.
6. Never imply that a live public webhook delivery was observed.
7. Describe external notification delivery as logged/simulated.
8. Show PR #268 as merged.
9. Do not expose credentials, recipient data, private account details, raw payloads, or full
   transcripts.
10. End on practical workflow, human review, and uncertainty preservation.

## Recording checklist

- [ ] Reset to a clean synthetic-data demo database if needed
- [ ] Pre-open dashboard, High Risk scenario, Live CALL-E Evidence, architecture, and PR #268 tabs
- [ ] Confirm no screen exposes `.env`, environment variables, phone numbers, or credentials
- [ ] If using an audio excerpt, keep it brief and pair it with a sanitized evidence screen
- [ ] Record at readable zoom and verify all text after export
- [ ] Confirm runtime is under 3:00
- [ ] Upload to the permitted public video host and test in an incognito window

Canonical evidence: [Live CALL-E Evidence](LIVE_CALLE_EVIDENCE.md) and
[Current Verification Status](CURRENT_VERIFICATION_STATUS.md).
