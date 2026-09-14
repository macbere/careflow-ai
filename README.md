# CareFlow AI

CareFlow AI is a post-discharge care-coordination prototype built for the
**CALL-E: Your Code Is Calling** hackathon. It uses CALL-E for structured follow-up calls,
preserves uncertain answers, applies an explainable risk rubric, and creates a human-review
workflow when evidence is concerning or unusable.

**Live judge demo:** https://careflowai.pythonanywhere.com  
**Health check:** https://careflowai.pythonanywhere.com/health

> **Synthetic data only.** This hackathon prototype is not HIPAA-reviewed and must not be
> connected to real Protected Health Information. It has no production authentication, RBAC,
> multi-tenancy, EHR integration, or compliance claim.

## Three-minute judge path

### Fastest path — hosted demo

Open **https://careflowai.pythonanywhere.com** and select **Run Demo Mode**, then run the
**High Risk** scenario. The public deployment is configured for the deterministic mock provider,
so judges do not need a CALL-E account, API key, phone number, or provider credits and no real
phone call is placed from Demo Mode.

### Local path

No CALL-E account, API key, phone number, or credits are required.

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
Demo Mode uses the deterministic `MockVoiceClient`: no real phone call occurs and no CALL-E
credits are consumed. It still exercises CareFlow's downstream orchestration, risk,
escalation, summary, acknowledgement, and timeline path.

See [Judge Quick-Start](docs/JUDGE_QUICKSTART.md) for the evaluation route,
[Live CALL-E Evidence](docs/LIVE_CALLE_EVIDENCE.md) for the two-layer real-provider proof, and
[Current Verification Status](docs/CURRENT_VERIFICATION_STATUS.md) for the authoritative current
boundaries.

## What the product demonstrates

- Provider-independent call orchestration through the `VoiceProviderClient` interface.
- A real CALL-E REST implementation with goal-driven tasks, plural `recipients`, per-recipient
  structured-result schema, explicit idempotency keys, and CareFlow metadata binding.
- A deterministic four-state normalization and risk pipeline that never silently converts
  missing, invalid, or `unknown` evidence into reassurance.
- A `needs_review` safety gate: unusable structured evidence creates no normal
  `RiskAssessment`, normal Care Summary, or clinical escalation.
- Explainable low/medium/high risk scoring for valid complete evidence.
- Genuine escalation and dashboard-acknowledgement state. Notification delivery is currently
  logged/simulated by `LogNotificationService`, not sent through SMS, email, Slack, or paging.
- A chronological audit timeline, care summary, operational panels, and executive KPIs.
- Five deterministic Demo Mode scenarios: Healthy Recovery, Moderate Concern, High Risk,
  Failed Call, and No Answer.
- A reusable, dependency-free CALL-E Agent Skill merged upstream in
  [CALL-E PR #268](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/268).

## Real CALL-E trust boundary

The public webhook body is treated only as an untrusted wake-up envelope:

```text
event ID + call ID envelope
  -> authenticated GET /v1/calls/{id}
  -> authenticated GET /v1/calls/{id}/events
  -> exact DeveloperEvent identity/type binding
  -> CareFlow reference_id + discharge_id metadata binding
  -> result-quality safety gate
  -> orchestration
```

Nonterminal provider state and authenticated-fetch failures return a retryable HTTP 503.
Terminal processing is idempotent for the tested sequential/retry paths and rejects conflicting
previously assessed evidence; this is not a claim of universal concurrent exactly-once
processing. Full detail is in [Architecture](docs/ARCHITECTURE.md).

## Setup and configuration

Python 3.10 or newer is required by the pinned dependencies. Mock mode is the safe default in
`.env.example`.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing; replace outside a throwaway local demo |
| `DATABASE_URL` | SQLAlchemy URL; defaults to local SQLite |
| `VOICE_PROVIDER` | `mock` by default, or `calle` for the real provider |
| `CALLE_API_KEY` | Required only for `VOICE_PROVIDER=calle` |
| `CALLE_API_BASE_URL` | Defaults to `https://api.heycall-e.com` |
| `CALLE_WEBHOOK_URL` | Optional per-call public webhook target |
| `CALLE_WEBHOOK_SECRET` | Unused forward-compatibility surface; not required by the current trust design |
| `NOTIFICATION_PROVIDER` | `log`; no external delivery provider is implemented |
| `LOG_LEVEL` | Application log level |

Never commit `.env`. Before a live call, confirm recipient consent, E.164 formatting,
provider-region support, and current CALL-E terms. Judges do not need live credentials.

## Tests

```bash
python -m pytest -q
```

`pytest.ini` limits discovery to `tests/` and the reusable contribution tests, so this command
does not collect credential-gated scripts in `validation-experiments/` and does not require
`CALLE_API_KEY`. Functional code freeze had 149 passing tests; the final
submission-hardening suite also has **149 passing tests** (one pre-existing SQLAlchemy
`Query.get()` `LegacyAPIWarning`).

Equivalent explicit command:

```bash
python -m pytest -q tests calle-contrib/structured-outcome-followup-call/scripts/test_orchestrate_example.py
```

## Two-layer live CALL-E evidence

CareFlow's real-provider evidence is intentionally split into two complementary layers rather
than presenting one test as proof of everything.

### 1. Historical human validation — real conversation and structured extraction

Earlier controlled CALL-E validation calls reached a consenting human respondent and produced
genuine turn-by-turn conversations.

- `call_3-bmAXd3HqzJWnK5Fg2Z6w` completed with `task_completed=true` and high completion
  confidence (0.96). All eight recovery answers were captured in the per-recipient structured
  result and matched the spoken conversation field-for-field.
- `call_dWj5VxQM2s4lhuFsRiRm8g` tested uncertainty deliberately. No numeric pain score was
  spoken; CALL-E returned `pain_level="unknown"` while preserving the other seven answers
  correctly. The result completed with high completion confidence (0.95).

These calls validate real human telephony plus CALL-E's structured-answer contract. They were
controlled provider-contract validations and are not presented as proof of the final CareFlow
webhook trust path.

### 2. Final frozen-build validation — real CALL-E task plus CareFlow trust path

On September 11, the verified frozen functional runtime created a genuine CALL-E call to the official
hackathon US testing hotline.

- `POST /v1/calls` returned HTTP **201** and the authenticated CallTask progressed from
  `queued` to `completed`.
- CALL-E returned `task_completed=true`, high task-completion confidence (0.86), matching
  `reference_id` / `discharge_id` metadata, a transcript, and a per-recipient structured result.
- The hotline interaction produced eight explicit `unknown` recovery answers.
- CareFlow retrieved the genuine bound terminal `call.completed` DeveloperEvent, re-fetched
  authoritative provider state, verified correlation metadata, and routed the result to
  `needs_review` with zero normal RiskAssessment, Care Summary, or Escalation artifacts.
- Sequential replay of the same genuine terminal event returned HTTP 200 and created no
  duplicate downstream artifacts.

This validates the final application's real CALL-E creation, authenticated provider-state
resolution, metadata binding, uncertainty handling, and tested replay behavior. It does **not**
claim that CALL-E delivered a webhook to a public CareFlow URL; the inbound event envelope was
initiated locally and the handler then performed its normal authenticated provider re-fetch.

### What the two layers prove together

The historical calls prove that CALL-E genuinely reached a human and converted spoken recovery
answers into structured evidence. The frozen-build run proves that the final CareFlow runtime
created a real CALL-E task and safely processed genuine provider evidence through its
authenticated trust boundary. Together they cover both sides of the product story without
misrepresenting either test.

A separate consenting Nigerian-destination Create Call attempt was rejected before dialing with
HTTP 422 `call_not_ready` because calling Nigeria in English was not currently supported. No
provider call ID was created; this is a provider region/language availability boundary.

See [Live CALL-E Evidence](docs/LIVE_CALLE_EVIDENCE.md) for the concise evidence matrix and
[Current Verification Status](docs/CURRENT_VERIFICATION_STATUS.md) for the canonical current
truth boundary.

## Repository map

```text
app/                            Flask app, models, and services
app/services/calle/             real + mock voice-provider implementations
app/services/notifications/     pluggable interface + log implementation
calle-contrib/                  merged reusable community Agent Skill
docs/                           judge, architecture, deployment, and submission material
tests/                          credential-free application suite
validation-experiments/         manual live experiments; excluded from pytest discovery
```

## Documentation

- [Live CALL-E Evidence](docs/LIVE_CALLE_EVIDENCE.md) — human-call proof + final frozen-build proof
- [Current Verification Status](docs/CURRENT_VERIFICATION_STATUS.md) — canonical current truth
- [Judge Quick-Start](docs/JUDGE_QUICKSTART.md) — credential-free evaluation
- [Architecture](docs/ARCHITECTURE.md) — components, trust boundary, safety gate
- [Demo Walkthrough](docs/DEMO_WALKTHROUGH.md) — product demonstration
- [Demo Recording Plan](docs/DEMO_RECORDING_PLAN.md) — truthful sub-three-minute script
- [Deployment Guide](docs/DEPLOYMENT.md) — mock demo and real-provider configuration
- [Devpost Submission Package](docs/DEVPOST_SUBMISSION.md) — paste-ready draft and owner actions

Licensed under the [MIT License](LICENSE).
