# Demo recording plan

Recording notes for **CALL-E: Your Code Is Calling**. The submitted video is available on
[YouTube](https://youtu.be/zMXSo5HUZ3o).

Target length: **2:40–2:50**, with a hard limit below **3:00**. Use the synthetic High Risk
scenario for the walkthrough; the plan does not require another live call.

## Sequence and narration

| Time | Screen | Point to cover |
|---|---|---|
| 0:00–0:18 | Dashboard | Introduce the follow-up problem and project |
| 0:18–0:42 | Dashboard | Show priorities, pending work, and KPIs |
| 0:42–1:24 | Demo Mode, High Risk | Run the mock scenario; inspect answers, score, reasons, and escalation |
| 1:24–1:50 | Call detail | Show summary, logged notification, acknowledgement, and timeline |
| 1:50–2:05 | Live evidence document | Explain the earlier calls with a human respondent |
| 2:05–2:27 | Live evidence and architecture | Explain the September 11 application test and its limit |
| 2:27–2:39 | GitHub | Show merged CALL-E PR #268 |
| 2:39–2:50 | Dashboard | Close on the human review workflow |

### Opening

“CareFlow is my project for helping a care coordinator follow up after discharge. It brings the
answers from a phone conversation into one place, with reasons for each priority and a record
of the follow-up.”

### Dashboard and High Risk scenario

“The dashboard shows pending work and unresolved escalations. I'll run the High Risk scenario
using synthetic data. This is a mock call outcome; no phone call is being placed. CareFlow
checks the answers, calculates a score, and explains why this case needs attention.”

### Human review

“The escalation is stored in the application. Notifications are currently logged, so this
hasn't sent an SMS or email. When I acknowledge the escalation, its status and timeline update.
The summary keeps the result and next step together.”

### Live validation

“CALL-E was also tested with a consenting human respondent. One call captured all eight recovery
answers correctly. Another left the pain score unknown when no number was given.

On September 11, the submission build created a real CALL-E task to the official test hotline.
CareFlow checked the returned call and event data, then sent the unknown answers to human
review. Replaying the event created no duplicate records. That test used the local webhook
route; public webhook delivery wasn't observed.”

### Contribution and close

“The reusable structured-outcome skill was merged into CALL-E's community repository as
pull request 268. CareFlow applies that pattern to a follow-up dashboard where a person can see
the evidence, review uncertainty, and acknowledge the work.”

## Recording checklist

- Prepare a clean synthetic demo and pre-open the dashboard, evidence record, architecture,
  and [PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268).
- Keep credentials, phone numbers, private account details, raw payloads, and full transcripts
  off screen. Call/event IDs are unnecessary in the video.
- Label Demo Mode as mock. Keep the earlier human-call tests separate from the application test.
- If using a consenting historical call excerpt, limit it to 5–7 seconds with a sanitized screen.
- Check text readability and runtime after export, then test the public video link while signed out.

Results to reference: [live evidence](LIVE_CALLE_EVIDENCE.md) and
[verification status](CURRENT_VERIFICATION_STATUS.md).
