# Judge Quick-Start

CareFlow AI can be evaluated end to end in mock mode without a CALL-E account, API key,
phone number, or credits.

## Run the product

```bash
git clone https://github.com/macbere/careflow-ai.git
cd careflow-ai
python -m venv venv
source venv/bin/activate          # Windows PowerShell: .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env             # Windows PowerShell: Copy-Item .env.example .env
python -m app.seed
python run.py
```

Open `http://localhost:5000/dashboard` → **Open Demo Mode** → **Run High Risk**.

This creates a synthetic patient and runs the downstream workflow through the deterministic
`MockVoiceClient`. **No real phone call occurs and no CALL-E credits are used.** The call detail
page shows structured evidence, explainable risk, escalation, logged notification state, Care
Summary, acknowledgement, and the audit timeline.

## Run the safe suite

```bash
python -m pytest -q
```

`pytest.ini` restricts collection to the credential-free application and contribution tests.
It excludes manual live scripts under `validation-experiments/`. The final safe suite has
**149 passing tests** with one pre-existing SQLAlchemy `Query.get()` `LegacyAPIWarning`.

## Verify meaningful CALL-E usage

- `app/services/calle/calle_client.py` builds the goal-driven task, plural `recipients`,
  aggregate and per-recipient schemas, CareFlow metadata, optional webhook URL, and an explicit
  attempt-unique `Idempotency-Key`; it uses `https://api.heycall-e.com`.
- `app/api/webhooks.py` treats an inbound webhook as an untrusted wake-up envelope and resolves
  it through authenticated call and DeveloperEvent retrieval before any database mutation.
- `app/services/call_orchestrator.py` verifies CareFlow metadata binding, applies the
  `needs_review` quality gate, and resumes the valid terminal workflow safely on replay.
- `app/services/calle/mock_client.py` implements the same interface for local development and
  Demo Mode; it is not live CALL-E evidence.

See [Architecture](ARCHITECTURE.md), [Live CALL-E Evidence](LIVE_CALLE_EVIDENCE.md), and
[Current Verification Status](CURRENT_VERIFICATION_STATUS.md).

## Verify the live-evidence story

CareFlow keeps its real-provider evidence in two separate layers:

- **Historical human validation:** genuine CALL-E calls reached a consenting human respondent
  and returned structured recovery answers matching the spoken conversation, including an
  explicit `unknown` pain value when no numeric score was given.
- **Final frozen-build validation:** the frozen CareFlow runtime created a genuine CALL-E task
  through the official hackathon US testing hotline and safely processed genuine terminal
  provider evidence through its authenticated trust path.

These two validations prove different parts of the product and are intentionally not presented
as one end-to-end public-webhook test.

## Verify the community contribution

The reusable `structured-outcome-followup-call` Agent Skill is under
`calle-contrib/structured-outcome-followup-call/` and was merged in
[CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268).

```bash
python calle-contrib/structured-outcome-followup-call/scripts/orchestrate_example.py
```

It is a dependency-free, non-healthcare demonstration of the general pattern:
call → structured result → deterministic rubric → downstream action.

## Important boundaries

- Demo Mode is mock-based; it is not presented as live-call evidence.
- A separate consenting Nigerian-destination attempt was rejected before dialing with HTTP 422
  `call_not_ready`; CALL-E stated that Nigeria in English was not currently supported.
- Actual public inbound webhook delivery has not been directly observed; authenticated
  trust/replay behavior is covered by automated tests and was exercised locally with a genuine
  terminal provider event.
- `LogNotificationService` logs/simulates delivery. No external messaging provider exists.
- Synthetic data only; not HIPAA-reviewed or production-ready.
