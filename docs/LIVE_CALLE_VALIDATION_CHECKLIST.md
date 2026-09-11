# Live CALL-E Validation — Current Record and Future Checklist

This document records what was actually validated and what remains unobserved. It is not an
instruction to place another call during submission hardening.

## Current evidence

- Historical genuine CALL-E calls reached a consenting human respondent and completed.
- Per-recipient structured results were retrieved successfully.
- One historical completed result preserved `pain_level="unknown"` rather than inventing a
  numeric value.
- On September 11, the frozen CareFlow runtime successfully created a genuine CALL-E call to
  the official hackathon US testing hotline with HTTP **201**.
- That authenticated CallTask progressed from `queued` to `completed`, returned a transcript,
  a per-recipient structured result, and matching CareFlow correlation metadata.
- CareFlow retrieved the bound terminal DeveloperEvent, re-fetched authoritative provider state,
  and safely routed the all-`unknown` result to `needs_review` with no normal clinical artifacts.
- Sequential replay of the same genuine terminal event created no duplicate downstream artifacts.
- A separate consenting Nigerian-destination Create Call attempt was rejected before dialing
  with HTTP **422** `call_not_ready`; CALL-E stated that Nigeria in English was not currently
  supported. No provider call ID was created for that attempt.
- Actual public inbound webhook delivery has not been directly observed.
- Authenticated resolution, forged-body rejection, DeveloperEvent identity/type checks,
  CareFlow metadata binding, nonterminal retry, sequential replay recovery, and terminal
  evidence conflict are covered by automated tests.

## Current configuration contract

```dotenv
VOICE_PROVIDER=calle
CALLE_API_KEY=<current-key>
CALLE_API_BASE_URL=https://api.heycall-e.com
CALLE_WEBHOOK_URL=https://your-public-host.example/api/webhooks/calle
CALLE_WEBHOOK_SECRET=
```

`CALLE_WEBHOOK_URL` is optional. `CALLE_WEBHOOK_SECRET` is unused and is not an HMAC/shared
secret requirement. The trust boundary is authenticated CallTask plus DeveloperEvent retrieval
and CareFlow metadata binding.

## Optional future live validation

Only perform another live validation with separate owner authorization, a consenting E.164
recipient in a currently supported region, and secure environment configuration. Never commit
or print the key, phone number, raw recipient payload, or transcript.

- [ ] Confirm current CALL-E terms and destination-region support before Create Call.
- [ ] Confirm the request returns a provider call ID before claiming a call was created.
- [ ] Confirm the consenting phone actually rings before claiming a dial occurred.
- [ ] Confirm terminal CallTask state and per-recipient structured result.
- [ ] Confirm any explicit `unknown` values are preserved by CareFlow.
- [ ] If testing public delivery, confirm the exact inbound webhook was observed independently
      of local replay.
- [ ] Confirm the envelope resolves through authenticated call and DeveloperEvent retrieval.
- [ ] Confirm `reference_id` and `discharge_id` metadata bind to the local call.
- [ ] Confirm valid complete evidence creates the expected assessment/summary/escalation path.
- [ ] Confirm unusable evidence creates `needs_review` with no normal clinical artifacts.
- [ ] Confirm notification output is described as logged/simulated unless a real adapter exists.

Do not claim universal concurrent exactly-once behavior from sequential replay tests.

Canonical current state: [Current Verification Status](CURRENT_VERIFICATION_STATUS.md).
