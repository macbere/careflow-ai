"""
Patients API.

Phase 2 adds patient creation (needed for the "create a synthetic patient"
step of the demo flow) and a timeline endpoint. Every synthetic MRN is
forced to a "SYN-" prefix here — not just documented as a convention — so
it's structurally impossible to create a patient row that looks like real
PHI through this API.
"""
import uuid

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.patient import Patient
from app.services import timeline_service
from app.services.timeline_service import get_timeline

patients_bp = Blueprint("patients", __name__, url_prefix="/api/patients")


@patients_bp.get("")
def list_patients():
    patients = Patient.query.order_by(Patient.created_at.desc()).all()
    return jsonify([p.to_dict() for p in patients])


@patients_bp.post("")
def create_patient():
    """
    Create a synthetic patient. `synthetic_mrn` is optional — if omitted, a
    fresh "SYN-" MRN is generated. If provided, it's still forced to carry
    the "SYN-" prefix, so this endpoint can never be used to store a
    real-looking MRN.
    """
    payload = request.get_json(force=True) or {}
    full_name = payload.get("full_name")
    phone_number = payload.get("phone_number")

    if not full_name or not phone_number:
        return jsonify({"error": "full_name and phone_number are required"}), 400

    mrn = payload.get("synthetic_mrn") or f"SYN-{uuid.uuid4().hex[:8].upper()}"
    if not mrn.upper().startswith("SYN-"):
        mrn = f"SYN-{mrn}"

    patient = Patient(full_name=full_name, synthetic_mrn=mrn, phone_number=phone_number)
    db.session.add(patient)
    db.session.flush()

    timeline_service.log_event(
        event_type="patient_created",
        title=f"Patient created: {patient.full_name}",
        description=f"Synthetic MRN {patient.synthetic_mrn}",
        patient_id=patient.id,
        commit=False,
    )
    db.session.commit()

    return jsonify(patient.to_dict()), 201


@patients_bp.get("/<int:patient_id>")
def get_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    data = patient.to_dict()
    data["discharges"] = [d.to_dict() for d in patient.discharges]
    return jsonify(data)


@patients_bp.get("/<int:patient_id>/timeline")
def get_patient_timeline(patient_id):
    Patient.query.get_or_404(patient_id)
    events = get_timeline(patient_id=patient_id)
    return jsonify([e.to_dict() for e in events])
