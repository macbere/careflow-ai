# Judge quick-start

CareFlow AI is a synthetic-data prototype for **CALL-E: Your Code Is Calling**.

## Hosted demo

Open the [dashboard](https://careflowai.pythonanywhere.com), select **Run Demo Mode**, and run
**High Risk**. Inspect the answers, score, reasons, escalation, Care Summary, and timeline.
Acknowledge the escalation to see its state change.

The hosted demo uses a deterministic mock provider. No account, API key, phone number, credits,
or real call is needed. Notification delivery is logged; no external message is sent.

[Watch the video](https://youtu.be/zMXSo5HUZ3o) ·
[Check service health](https://careflowai.pythonanywhere.com/health)

## Local setup

Requires Python 3.10 or newer.

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

Open `http://localhost:5000/dashboard`, select **Open Demo Mode**, then **Run High Risk**.
For the other scenarios and a longer tour, see the [walkthrough](DEMO_WALKTHROUGH.md).

## Automated tests

```bash
python -m pytest -q
```

The submission suite has **149 passing tests**, with one existing SQLAlchemy `Query.get()`
`LegacyAPIWarning`. `pytest.ini` excludes manual live experiments; the suite needs no API key.

## Inspect the CALL-E integration

| File | What to look for |
|---|---|
| `app/services/calle/calle_client.py` | Goal-driven requests, recipients, result schemas, metadata, callback URL, and idempotency keys |
| `app/api/webhooks.py` | Authenticated call/event retrieval before processing an inbound notification |
| `app/services/call_orchestrator.py` | Local metadata checks, result-quality gate, workflow processing, and sequential replay handling |
| `app/services/calle/mock_client.py` | The mock provider used for deterministic tests and demonstrations |

The [architecture](ARCHITECTURE.md) explains the request and processing paths.

## Live validation

Earlier CALL-E tests reached a consenting human and extracted structured recovery answers. The
September 11 submission-build test created a real task to the official hotline and processed its
authenticated results through the local webhook route. These tested different parts of the
integration. **Public inbound webhook delivery was not observed.**

See the [live evidence record](LIVE_CALLE_EVIDENCE.md) for individual results, including the
Nigerian-destination attempt that CALL-E rejected before dialing. The
[verification status](CURRENT_VERIFICATION_STATUS.md) lists remaining limits.

## Community contribution

The reusable `structured-outcome-followup-call` Agent Skill was merged in
[CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268).

```bash
python calle-contrib/structured-outcome-followup-call/scripts/orchestrate_example.py
```

This dependency-free example uses a non-healthcare delivery scenario. A copy and tests are in
`calle-contrib/structured-outcome-followup-call/`.

CareFlow is not HIPAA-reviewed or ready for real patient use. Enter synthetic data only.
