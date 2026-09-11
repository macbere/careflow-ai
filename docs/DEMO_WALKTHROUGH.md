# Demo Walkthrough

## Recommended one-click path

1. Start the app with `VOICE_PROVIDER=mock` and open `http://localhost:5000/dashboard`.
2. Select **Open Demo Mode**.
3. Select **Run High Risk**.
4. On the call detail page, show the structured evidence, deterministic score, reasons,
   recommended action, escalation, Care Summary, and timeline.
5. Acknowledge the escalation and show the real state/timeline update.

Demo Mode uses `MockVoiceClient`. It creates a synthetic patient and simulated provider outcome;
no phone is dialed and no CALL-E credits are consumed. The downstream orchestrator is the same
one used after a trusted real-provider event.

The escalation is genuine application state. Notification delivery is currently
logged/simulated through `LogNotificationService`; external SMS, email, Slack, or paging is not
implemented. Acknowledgement is a genuine application-state transition.

## Optional contrast: `needs_review`

Use an automated test explanation or a prepared synthetic review record to show that incomplete,
invalid, missing, null, or explicitly unknown structured evidence does not enter the normal
clinical path. CareFlow preserves it as `needs_review` and creates no normal RiskAssessment,
normal Care Summary, or clinical escalation.

Do not alter Demo Mode or run a credential-gated validation script merely to show this point.

## What to say about real CALL-E

Point to `app/services/calle/calle_client.py`, `app/api/webhooks.py`, and
`app/services/call_orchestrator.py`:

- outbound calls use a goal-driven task, plural recipients, aggregate and per-recipient
  schemas, CareFlow metadata, and an attempt-unique idempotency key;
- the webhook body is an untrusted wake-up envelope, not clinical truth;
- CareFlow authenticates call and DeveloperEvent retrieval, binds exact event/call identity and
  local metadata, then applies the result-quality gate;
- nonterminal/fetch failures return retryable HTTP 503; tested sequential replays avoid
  duplicate artifacts, without claiming universal concurrent exactly-once behavior.

Present the live evidence in two layers. Historical controlled CALL-E calls reached a consenting
human respondent and verified structured extraction, including preservation of an unavailable
pain score as `unknown`. Separately, the frozen CareFlow runtime successfully created a genuine
CALL-E call through the official hackathon US testing hotline and processed genuine terminal
provider evidence through the authenticated trust path. Actual public inbound webhook delivery
was not directly observed.

A separate consenting Nigerian-destination attempt was rejected before dialing with HTTP 422
`call_not_ready`, with CALL-E stating that Nigeria in English was not currently supported. No
provider call ID was created for that attempt.

## Community contribution

Show `calle-contrib/structured-outcome-followup-call/` and the official merged
[CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268). The standalone
example uses a non-healthcare delivery-exception domain and requires no application setup:

```bash
python calle-contrib/structured-outcome-followup-call/scripts/orchestrate_example.py
```

For the timed narration, use [Demo Recording Plan](DEMO_RECORDING_PLAN.md). For all current
evidence boundaries, use [Current Verification Status](CURRENT_VERIFICATION_STATUS.md).
