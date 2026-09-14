# CareFlow AI

CareFlow is my post-discharge follow-up prototype for the **CALL-E: Your Code Is Calling**
hackathon. It uses CALL-E to ask recovery questions over the phone, then brings the answers,
follow-up priorities, and review history into one dashboard.

My focus is the handoff from a conversation to a person who can act on it. A coordinator should
be able to see why a case was flagged, what information is missing, and whether someone has
acknowledged the follow-up.

[Try the demo](https://careflowai.pythonanywhere.com) ·
[Watch the video](https://youtu.be/zMXSo5HUZ3o) ·
[Devpost submission](https://devpost.com/software/careflow-ai-8z1p0u)

> **Synthetic data only.** CareFlow is a hackathon prototype, not a service for real patient
> care. It is not HIPAA-reviewed and has no production authentication, role-based access,
> tenant isolation, or EHR integration. Do not enter real Protected Health Information (PHI).

## Try it

Open the [hosted demo](https://careflowai.pythonanywhere.com), choose **Run Demo Mode**, and run
**High Risk**. The call detail page shows the recovery answers, risk score and reasons,
escalation, Care Summary, and timeline. Acknowledge the escalation to see the record update.

The hosted demo uses synthetic data and a deterministic mock provider. It requires no account,
API key, phone number, or credits, and places no phone calls. It runs the same downstream
workflow used after CareFlow has verified a real provider result. The
[health endpoint](https://careflowai.pythonanywhere.com/health) is also public.

## How it works

1. A discharge record starts a follow-up call through a common voice-provider interface.
2. CALL-E returns eight structured recovery answers. CareFlow preserves the raw result.
3. Missing, invalid, incomplete, or explicitly unknown answers put the call in `needs_review`.
   These cases receive no normal RiskAssessment, Care Summary, or clinical escalation.
4. Complete, valid answers pass to a rule-based scoring rubric with low, medium, or high
   priority and a list of reasons.
5. A high-risk result creates an escalation. A coordinator can acknowledge it in the dashboard;
   the summary and timeline record the workflow.

One design choice matters throughout: an unanswered question must stay unanswered. CareFlow
keeps uncertainty visible for human review. Its scoring and summaries use deterministic rules;
CALL-E handles the voice conversation and structured extraction.

Notifications currently use `LogNotificationService`. Escalations and acknowledgements are
stored in the application, but delivery is logged: no SMS, email, Slack, or paging service is
connected.

### Verifying provider results

The webhook body supplies event and call identifiers. Before processing a result, CareFlow
retrieves the call and its DeveloperEvents through authenticated CALL-E requests, checks the
exact event identity and type, and matches `reference_id` and `discharge_id` to local records.

Provider-fetch failures and nonterminal state return a retryable HTTP 503. Sequential replay
and retry tests cover duplicate handling; concurrent exactly-once processing is not guaranteed.
See the [architecture](docs/ARCHITECTURE.md) for request fields, error responses, and data flow.

## Run locally

Requires Python 3.10 or newer. No CALL-E credentials are needed for mock mode.

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
The other scenarios are Healthy Recovery, Moderate Concern, Failed Call, and No Answer.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing; replace outside a throwaway local demo |
| `DATABASE_URL` | SQLAlchemy URL; defaults to local SQLite |
| `VOICE_PROVIDER` | `mock` by default; `calle` selects the real provider |
| `CALLE_API_KEY` | Required for the real provider |
| `CALLE_API_BASE_URL` | Defaults to `https://api.heycall-e.com` |
| `CALLE_WEBHOOK_URL` | Optional public callback URL sent with each call |
| `CALLE_WEBHOOK_SECRET` | Unused; not required by the current webhook implementation |
| `NOTIFICATION_PROVIDER` | `log` is the only implemented channel |
| `LOG_LEVEL` | Application log level |

Keep `.env` out of Git. Before any live test, check recipient consent, phone-number format,
destination support, and CALL-E terms. See the [deployment guide](docs/DEPLOYMENT.md).

## Tests and live validation

```bash
python -m pytest -q
```

The submission suite has **149 passing tests**, with one existing SQLAlchemy `Query.get()`
`LegacyAPIWarning`. `pytest.ini` includes the application and reusable contribution tests and
excludes manual live scripts in `validation-experiments/`; no API key is needed.

Live validation covered two separate parts of the integration:

- Earlier calls reached a consenting human and returned structured answers matching the
  conversation, including an `unknown` pain score when no number was given.
- On September 11, the submission build created a real CALL-E task to the official test hotline.
  CareFlow verified the returned provider evidence and routed eight unknown answers to human
  review. Replaying the terminal event created no duplicate records.

The second test supplied the event to the local webhook route. **Public inbound webhook
delivery was not observed.** A separate Nigerian-destination attempt was rejected before
dialing with HTTP 422 `call_not_ready`; CALL-E reported that Nigeria in English was unsupported
at the time.

The [live evidence record](docs/LIVE_CALLE_EVIDENCE.md) contains the results and their limits.
[Verification status](docs/CURRENT_VERIFICATION_STATUS.md) lists what remains unverified.

## Community contribution

The reusable `structured-outcome-followup-call` Agent Skill was merged into CALL-E's community
repository in [PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268). It uses a
non-healthcare delivery example to demonstrate the same call, structured-result, rubric, and
follow-up pattern. A copy and its tests are in `calle-contrib/`.

## Find your way around

| Path | Contents |
|---|---|
| `app/` | Flask routes, models, services, and dashboard |
| `app/services/calle/` | Real and mock voice providers |
| `app/services/notifications/` | Notification interface and logging implementation |
| `calle-contrib/` | Reusable community contribution |
| `docs/` | Setup, architecture, validation, and submission records |
| `tests/` | Application tests |
| `validation-experiments/` | Manual live experiments, excluded from pytest discovery |

For a guided tour, use the [judge quick-start](docs/JUDGE_QUICKSTART.md) or
[demo walkthrough](docs/DEMO_WALKTHROUGH.md). The
[recording plan](docs/DEMO_RECORDING_PLAN.md) and
[submission record](docs/DEVPOST_SUBMISSION.md) document the hackathon presentation.

## Project ownership

CareFlow AI was created by [Macdonald (macbere)](https://github.com/macbere) and is licensed under the [MIT License](LICENSE).
