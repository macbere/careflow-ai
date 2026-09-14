# Verification status

This is the status of CareFlow's hackathon submission. Detailed call results are kept in the
[live evidence record](LIVE_CALLE_EVIDENCE.md).

| Area | Verified result | Remaining limit |
|---|---|---|
| Automated tests | 149 passed before and after submission hardening | One existing SQLAlchemy `Query.get()` `LegacyAPIWarning` |
| Human calls | CALL-E reached a consenting respondent and extracted recovery answers, including an explicit unknown value | These earlier tests covered the provider contract, not the final application webhook path |
| September 11 application test | The submission build created a real CALL-E task and processed authenticated call/event data | The event was submitted to the local Flask route; public inbound delivery was not observed |
| Unusable answers | Eight unknown answers produced `needs_review`, one review timeline event, and no normal clinical artifacts | This validates the review path, not a clinical outcome |
| Sequential replay | Repeating the same terminal event returned HTTP 200 without duplicate artifacts | Concurrent exactly-once processing is not guaranteed |
| Nigeria attempt | CALL-E returned HTTP 422 `call_not_ready` before dialing; no provider call ID was created | Nigeria in English was unsupported at the time; there was no retry |

## What the application currently supports

- Demo Mode uses `MockVoiceClient`, with five deterministic scenarios and no phone calls or
  provider credits.
- Real-provider results are fetched through authenticated call and DeveloperEvent requests.
  CareFlow checks event identity/type and local correlation metadata before processing.
- Missing, invalid, incomplete, null, or explicitly unknown structured answers are kept for
  human review. They create no normal RiskAssessment, Care Summary, or clinical escalation.
- Complete, valid results can produce a risk assessment, summary, and high-risk escalation.
  Dashboard acknowledgement updates the stored escalation and timeline.
- `LogNotificationService` records simulated delivery. No external SMS, email, Slack, or
  paging channel is implemented.

Automated tests cover forged envelopes, identity and metadata mismatches, provider-fetch
failures, nonterminal retries, result quality, conflicting terminal evidence, and sequential
replay recovery. The [architecture](ARCHITECTURE.md) describes those paths.

## Demo scope and current limitations

**Intended use.** CareFlow is a demonstration prototype for synthetic data. It is not intended
for real patient information, is not HIPAA-reviewed, and makes no compliance claim.

**Production capabilities.** User authentication, staff permissions (role-based access),
separation between organizations (tenant isolation), and connections to hospital record systems
(EHR integration) are not implemented.

**Public documentation privacy.** Credentials, recipient phone numbers, private account details,
and raw transcripts are omitted from the public evidence documents. This describes what is
published; it does not establish that the application is ready to handle real patient data.

## Submission version record

The September 11, 2026 submission build, preserved in the
[initial public release](https://github.com/macbere/careflow-ai/commit/7a91a4dcbe812ca56b9a34a87cbaf5e46bff4557),
is the baseline for the validation results on this page.

A September 14, 2026 review confirmed that the current executable Python logic matches that
baseline. Later application versions should record their own test results and live-validation
evidence.
