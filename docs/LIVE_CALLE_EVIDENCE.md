# Live CALL-E validation

CareFlow was tested with CALL-E in two settings: earlier calls with a consenting human, and a
September 11 test of the submission build against the official hackathon US hotline. They
exercise different parts of the integration.

| Test | Observed result | Scope |
|---|---|---|
| Earlier human calls | Spoken recovery answers were returned as structured fields, including an unknown value | Telephony and structured extraction |
| September 11 submission build | A real call task completed; CareFlow verified its provider data, routed unknown answers to review, and handled replay | Call creation and application processing through the local webhook route |
| Demo Mode | Deterministic scenarios exercise the downstream workflow | Synthetic product demonstration; no phone call |

Public inbound webhook delivery was not observed. Recipient phone numbers, credentials,
private account details, and raw transcripts are excluded from this record.

## Earlier human calls

### Complete recovery answers

Provider call ID: `call_3-bmAXd3HqzJWnK5Fg2Z6w`

- Create Call returned HTTP **201** and reached a consenting human respondent.
- The task completed with `status="completed"` and `task_completed=true`.
- `recipients[0].structured_result` contained all eight recovery answers. Each value matched
  the spoken conversation in the preserved transcript.
- CALL-E completion confidence was **high / 0.96**, with no failure code or message.

### An unanswered pain question

Provider call ID: `call_dWj5VxQM2s4lhuFsRiRm8g`

- Create Call returned HTTP **201** and completed with `task_completed=true`.
- The respondent gave no numeric pain score. CALL-E returned `pain_level="unknown"` and
  preserved the other seven answers correctly.
- CALL-E completion confidence was **high / 0.95**.

These were controlled tests of CALL-E's conversation and result contract. They did not run
those conversations through the final CareFlow webhook resolver.

## September 11 submission-build test

The verified submission runtime made exactly one Create Call request to the official hackathon
US testing hotline.

### Provider response

- `POST /v1/calls` returned HTTP **201** and a provider call ID.
- Authenticated CallTask state progressed from `queued` to `completed`, with
  `task_completed=true` and completion confidence **high / 0.86**.
- A transcript and per-recipient structured result were returned. All eight recovery answers
  were explicitly `unknown`; the hotline supplied no usable patient answers.
- Returned `reference_id` and `discharge_id` metadata matched CareFlow's local records.
- Authenticated DeveloperEvent retrieval returned a matching terminal `call.completed` event.

The confidence values in this document describe CALL-E task completion, not clinical risk.

### Application processing

The genuine event ID and call ID were supplied to the local Flask webhook route. The handler
then fetched the call and DeveloperEvents through authenticated requests, verified the event
identity/type and correlation metadata, and passed the result to the quality gate.

| Observation | Result |
|---|---|
| Webhook response | HTTP **200** |
| Call and discharge status | `needs_review` |
| Normal RiskAssessments | **0** |
| Normal Care Summaries | **0** |
| Clinical Escalations | **0** |
| Review timeline events | **1** |
| Sequential replay of the same event | HTTP **200**, with all artifact counts unchanged |

This exercised real call creation, authenticated state retrieval, metadata binding, uncertainty
handling, and sequential replay in the submission build. Since the inbound event was supplied
locally, it did not verify CALL-E delivery to a public CareFlow endpoint. The
[architecture](ARCHITECTURE.md) describes the resolver and retry behavior.

## Nigerian-destination attempt

A separate test, with consent and a valid credential, attempted a call to Nigeria. CALL-E
rejected it before dialing with HTTP **422** and `call_not_ready`, reporting that Nigeria in
English was unsupported at the time. No provider call ID was created, no phone call occurred,
and no retry was made. The response identified a destination/language restriction.

## Next engineering steps

- **Validation: public webhook delivery.** The handler has processed genuine provider data
  through the local route. Verify CALL-E delivery to the public endpoint independently of
  local replay.
- **Validation: simultaneous events.** Sequential replay and retry handling have been tested.
  Check what happens when copies of an event arrive at the same time, and address any duplicate
  records or inconsistent results.
- **Implementation and validation: external notifications.** The current adapter only logs
  notification requests. Add an email, SMS, or other delivery adapter, then verify that messages
  reach the intended recipient.

For the application test status, demo scope, and current limitations, see
[verification status](CURRENT_VERIFICATION_STATUS.md). Future live tests are covered by the
[validation checklist](LIVE_CALLE_VALIDATION_CHECKLIST.md).
