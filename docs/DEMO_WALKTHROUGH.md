# Demo walkthrough

## Run a scenario

1. Open the [hosted dashboard](https://careflowai.pythonanywhere.com), or start the app locally
   with `VOICE_PROVIDER=mock` and open `http://localhost:5000/dashboard`.
2. Open Demo Mode and choose **High Risk**.
3. On call detail, inspect the structured answers, score and reasons, recommended action,
   escalation, Care Summary, and timeline.
4. Acknowledge the escalation and check the status and timeline update.

Demo Mode creates a synthetic patient and a simulated provider outcome. It places no call and
uses no CALL-E credits, even when the normal voice provider is configured as `calle`. It uses
the same downstream orchestrator as verified real-provider results.

The escalation and acknowledgement are stored application state. `LogNotificationService`
records simulated delivery; external SMS, email, Slack, and paging are not implemented.

## Other scenarios

| Scenario | Expected result |
|---|---|
| Healthy Recovery | Low risk, summary, no escalation |
| Moderate Concern | Medium risk, summary, no escalation |
| High Risk | High risk, escalation, and summary |
| Failed Call | Failed status, no risk assessment or summary |
| No Answer | No-answer status, no risk assessment or summary |

## Explain missing information

Use the automated tests or a prepared synthetic review record to show `needs_review`. This is
not one of the five Demo Mode buttons. Missing, invalid, incomplete, null, or explicitly unknown
answers are preserved for a person to review, with no normal RiskAssessment, Care Summary, or
clinical escalation. Demonstrating this path does not require a live call.

## Explain the real integration

The [architecture](ARCHITECTURE.md) follows a real call from the outbound request through
provider verification and the result-quality gate. The [live evidence record](LIVE_CALLE_EVIDENCE.md)
keeps the earlier human-call tests separate from the September 11 application test. The latter
used a real provider event through the local webhook route; public inbound delivery was not
observed. The evidence record also documents the Nigerian-destination rejection before dialing.

## Show the contribution

Open [merged CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268).
The standalone example is also available locally:

```bash
python calle-contrib/structured-outcome-followup-call/scripts/orchestrate_example.py
```

It uses a non-healthcare delivery scenario and requires no application setup or credentials.
Use the [recording plan](DEMO_RECORDING_PLAN.md) for a timed tour and
[verification status](CURRENT_VERIFICATION_STATUS.md) for current limits.
