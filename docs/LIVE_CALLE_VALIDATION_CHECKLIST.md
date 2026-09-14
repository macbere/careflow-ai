# Live validation checklist

Use this checklist for a future, separately approved live test. The existing submission results
are recorded in [live evidence](LIVE_CALLE_EVIDENCE.md); this checklist is not a record of a new
call or an instruction to place one.

## Setup

Obtain the Project Owner's approval and the recipient's consent. Check CALL-E's current terms,
E.164 phone formatting, and destination/language support. The earlier Nigerian-destination
attempt was rejected before dialing, so support must be checked again before any future test.

```dotenv
VOICE_PROVIDER=calle
CALLE_API_KEY=<current-key>
CALLE_API_BASE_URL=https://api.heycall-e.com
CALLE_WEBHOOK_URL=https://your-public-host.example/api/webhooks/calle
CALLE_WEBHOOK_SECRET=
```

`CALLE_WEBHOOK_URL` is optional. `CALLE_WEBHOOK_SECRET` is unused. CareFlow verifies results by
fetching authenticated CallTask and DeveloperEvent data and checking local correlation metadata.
Keep keys, phone numbers, raw recipient payloads, and transcripts out of public logs and Git.

## Checks

- [ ] Record the Create Call response and confirm a provider call ID was returned.
- [ ] Confirm with the consenting recipient whether the phone rang.
- [ ] Retrieve terminal CallTask state and the per-recipient structured result.
- [ ] Check that spoken answers, including explicit unknown values, match the returned fields.
- [ ] If testing public delivery, record the inbound webhook independently of local replay.
- [ ] Check authenticated event identity/type and the `reference_id` / `discharge_id` binding.
- [ ] Check the assessment, summary, and escalation path for valid, complete evidence.
- [ ] Check that unusable evidence becomes `needs_review`, with no normal clinical artifacts.
- [ ] Replay the terminal event and check for duplicate records.
- [ ] Record notification output as logged/simulated unless a real adapter is in use.

Sequential replay results do not establish concurrent exactly-once processing. Update the
[evidence record](LIVE_CALLE_EVIDENCE.md) and [verification status](CURRENT_VERIFICATION_STATUS.md)
with the observed results and any remaining gaps.
