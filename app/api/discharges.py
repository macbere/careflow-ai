"""Discharges API — create discharges and trigger their follow-up call."""
from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models.discharge import Discharge
from app.models.patient import Patient
from app.services import timeline_service
from app.services.call_orchestrator import CallOrchestrator
from app.services.calle import get_voice_client
from app.services.notifications import get_notification_service

discharges_bp = Blueprint("discharges", __name__, url_prefix="/api/discharges")


@discharges_bp.get("")
def list_discharges():
    discharges = Discharge.query.order_by(Discharge.discharge_date.desc()).all()
    return jsonify([d.to_dict() for d in discharges])


@discharges_bp.post("")
def create_discharge():
    payload = request.get_json(force=True) or {}
    patient_id = payload.get("patient_id")
    diagnosis = payload.get("diagnosis")

    if not patient_id or not diagnosis:
        return jsonify({"error": "patient_id and diagnosis are required"}), 400

    patient = Patient.query.get(patient_id)
    if patient is None:
        return jsonify({"error": f"No patient with id {patient_id}"}), 404

    discharge = Discharge(patient_id=patient.id, diagnosis=diagnosis)
    db.session.add(discharge)
    db.session.flush()

    timeline_service.log_event(
        event_type="patient_discharged",
        title=f"{patient.full_name} discharged",
        description=f"Diagnosis: {diagnosis}",
        patient_id=patient.id,
        discharge_id=discharge.id,
        commit=False,
    )
    db.session.commit()

    return jsonify(discharge.to_dict()), 201


@discharges_bp.post("/<int:discharge_id>/initiate-call")
def initiate_call(discharge_id):
    """
    Trigger the follow-up call for a discharge. This is the entry point to
    the Discharge -> CALL-E call -> webhook -> risk engine -> care summary
    workflow.
    """
    discharge = Discharge.query.get_or_404(discharge_id)

    voice_client = get_voice_client(current_app.config)
    notification_service = get_notification_service(current_app.config)
    orchestrator = CallOrchestrator(voice_client, notification_service)
    call = orchestrator.initiate_follow_up_call(discharge)

    return jsonify(call.to_dict()), 202
