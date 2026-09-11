"""
Webhooks API — receives inbound call-completion events from the voice
provider (real CALL-E in production, unused in mock mode since the mock
client's simulation is triggered directly via /api/calls/<id>/simulate-completion).
"""
from flask import Blueprint, current_app, jsonify, request

from app.extensions import logger
from app.services.call_orchestrator import CallOrchestrator
from app.services.calle import get_voice_client
from app.services.calle.base import (
    AuthoritativeSnapshotUnavailableError,
    InvalidWebhookEnvelopeError,
    NonterminalSnapshotError,
    ProviderCallBindingError,
    TerminalEvidenceConflictError,
)
from app.services.notifications import get_notification_service

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


@webhooks_bp.post("/calle")
def calle_webhook():
    voice_client = get_voice_client(current_app.config)

    # The webhook body is only a wake-up envelope. The provider resolves it
    # into a trusted event by authenticated GET before any database mutation.
    try:
        event = voice_client.resolve_webhook_event(
            dict(request.headers), request.get_data()
        )
    except InvalidWebhookEnvelopeError as exc:
        logger.warning("Rejected invalid CALL-E webhook envelope: %s", exc)
        return jsonify({"error": str(exc)}), 401
    except NonterminalSnapshotError as exc:
        logger.info("CALL-E state is not terminal; requesting webhook retry: %s", exc)
        return jsonify({"error": str(exc), "status": "retry"}), 503
    except AuthoritativeSnapshotUnavailableError as exc:
        logger.warning("Deferred CALL-E webhook because GET failed: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except ProviderCallBindingError as exc:
        logger.warning("Rejected CALL-E webhook with mismatched provider IDs: %s", exc)
        return jsonify({"error": str(exc)}), 409

    notification_service = get_notification_service(current_app.config)
    orchestrator = CallOrchestrator(voice_client, notification_service)
    try:
        call = orchestrator.process_event(event)
    except TerminalEvidenceConflictError as exc:
        logger.error("Webhook terminal evidence conflict: %s", exc)
        return jsonify({"error": str(exc)}), 409
    except ProviderCallBindingError as exc:
        logger.error("Webhook binding failed: %s", exc)
        return jsonify({"error": str(exc)}), 409
    except ValueError as exc:
        logger.error("Webhook processing failed: %s", exc)
        return jsonify({"error": str(exc)}), 404

    return jsonify(call.to_dict())
