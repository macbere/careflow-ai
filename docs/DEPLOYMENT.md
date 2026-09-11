# Deployment Guide

## Credential-free local demo

Python 3.10 or newer is required by the pinned dependencies.

```bash
python -m venv venv
source venv/bin/activate          # Windows PowerShell: .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env             # Windows PowerShell: Copy-Item .env.example .env
python -m app.seed
python run.py
```

Open `http://localhost:5000/dashboard`. The example environment uses
`VOICE_PROVIDER=mock`; no CALL-E credentials, calls, or credits are involved. Demo Mode always
uses `MockVoiceClient`, even if the normal application provider is configured as `calle`.

## Real CALL-E configuration

Use the real provider only with consent, an authorized E.164 recipient, and confirmed provider
support for the destination region. Region availability can vary; do not assume Nigerian
outbound support. A consenting Nigerian-destination validation attempt was rejected before
dialing with HTTP 422 `call_not_ready`, with CALL-E stating that Nigeria in English was not
currently supported.

```dotenv
VOICE_PROVIDER=calle
CALLE_API_KEY=<your-current-key>
CALLE_API_BASE_URL=https://api.heycall-e.com
CALLE_WEBHOOK_URL=https://your-public-host.example/api/webhooks/calle
CALLE_WEBHOOK_SECRET=
```

- `CALLE_WEBHOOK_URL` is optional. Set it only when a specific publicly reachable HTTPS
  callback should be sent with each Create Call request; otherwise leave it blank.
- `CALLE_WEBHOOK_SECRET` is currently unused and is not required. It remains only as a
  forward-compatibility surface if CALL-E later documents a signing mechanism.
- Store `CALLE_API_KEY` in the deployment platform's secret manager or environment settings.
  Never commit `.env` or expose it in a recording.

## Webhook trust model

The webhook endpoint must be publicly reachable over HTTPS for actual provider delivery.
CareFlow does not trust clinical fields in the inbound body and does not rely on an undocumented
HMAC secret. It extracts and cross-checks the event/call envelope, then performs authenticated
call and DeveloperEvent retrieval, exact event identity/type binding, and CareFlow
`reference_id`/`discharge_id` metadata binding before orchestration. Provider-fetch or
nonterminal conditions return HTTP 503 so the delivery can be retried.

Actual public inbound webhook delivery has not been directly observed in this project; the
trust, rejection, retry, and sequential-replay paths are covered by automated tests. See
[Current Verification Status](CURRENT_VERIFICATION_STATUS.md).

## Hosting notes

Any Python host with a persistent database and HTTPS ingress can run the Flask application.
For a public demo:

1. Install `requirements.txt` and run the app behind a production WSGI server supported by the
   chosen platform; `python run.py` is the local development entry point.
2. Configure environment values in the host, never in source control.
3. Use a persistent disk for SQLite or configure a managed database through `DATABASE_URL`.
4. Run `python -m app.seed` only when synthetic baseline records are wanted.
5. Configure `GET /health` as the platform health check.

## Healthcare production boundary

This deployment guidance is for a synthetic-data hackathon demo. CareFlow is not
HIPAA-reviewed and does not currently provide production authentication, RBAC, tenant
isolation, EHR integration, security operations, retention controls, or a compliance program.
Do not deploy it with real PHI.

Notifications use `LogNotificationService`: the application creates real escalation state and
records simulated/logged delivery, but it does not send external SMS, email, Slack, or pages.
