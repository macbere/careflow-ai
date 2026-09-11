"""Calls API — call history, care summary, timeline, plus a mock-mode demo helper."""
from flask import Blueprint, current_app, jsonify, request

from app.models.call import FollowUpCall
from app.services.call_orchestrator import CallOrchestrator
from app.services.calle import get_voice_client
from app.services.calle.mock_client import MockVoiceClient
from app.services.calle.base import CallRequest
from app.services.notifications import get_notification_service
from app.services.recovery_questions import STANDARD_RECOVERY_QUESTIONS
from app.models.timeline_event import TimelineEvent

calls_bp = Blueprint("calls", __name__, url_prefix="/api/calls")


@calls_bp.get("")
def list_calls():
    calls = FollowUpCall.query.order_by(FollowUpCall.initiated_at.desc()).all()
    return jsonify([c.to_dict() for c in calls])


@calls_bp.get("/<int:call_id>")
def get_call(call_id):
    call = FollowUpCall.query.get_or_404(call_id)
    data = call.to_dict()
    if call.risk_assessment:
        data["risk_assessment"] = call.risk_assessment.to_dict()
        if call.risk_assessment.escalation:
            data["escalation"] = call.risk_assessment.escalation.to_dict()
    if call.care_summary:
        data["care_summary"] = call.care_summary.to_dict()
    return jsonify(data)


@calls_bp.get("/<int:call_id>/care-summary")
def get_care_summary(call_id):
    call = FollowUpCall.query.get_or_404(call_id)
    if not call.care_summary:
        return jsonify({"error": "Care summary not yet available for this call"}), 404
    return jsonify(call.care_summary.to_dict())


@calls_bp.get("/<int:call_id>/timeline")
def get_call_timeline(call_id):
    FollowUpCall.query.get_or_404(call_id)
    events = (
        TimelineEvent.query.filter_by(call_id=call_id).order_by(TimelineEvent.created_at.asc()).all()
    )
    return jsonify([e.to_dict() for e in events])


@calls_bp.post("/<int:call_id>/simulate-completion")
def simulate_completion(call_id):
    """
    Demo/dev-only helper: only available when VOICE_PROVIDER=mock. Simulates
    CALL-E finishing a call and firing its webhook, so the full pipeline
    (webhook -> risk engine -> escalation -> care summary) can be demoed
    without waiting on a real phone call.

    Body: {"scenario": "low_risk" | "high_risk" | "random"}
    """
    if current_app.config["VOICE_PROVIDER"] != "mock":
        return jsonify({"error": "simulate-completion is only available when VOICE_PROVIDER=mock"}), 400

    call = FollowUpCall.query.get_or_404(call_id)
    if not call.provider_call_id:
        return jsonify({"error": "Call has no provider_call_id yet — initiate the call first"}), 400

    scenario = (request.get_json(silent=True) or {}).get("scenario", "random")

    mock_client = MockVoiceClient()
    call_request = CallRequest(
        patient_name=call.discharge.patient.full_name,
        phone_number=call.discharge.patient.phone_number,
        discharge_diagnosis=call.discharge.diagnosis,
        questions=STANDARD_RECOVERY_QUESTIONS,
        reference_id=str(call.id),
    )
    payload = mock_client.simulate_completed_call(call.provider_call_id, call_request, scenario=scenario)

    notification_service = get_notification_service(current_app.config)
    orchestrator = CallOrchestrator(mock_client, notification_service)
    updated_call = orchestrator.process_webhook_event(payload)

    return jsonify(updated_call.to_dict())
