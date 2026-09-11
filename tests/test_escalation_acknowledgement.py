from app.models.call import FollowUpCall
from app.models.discharge import Discharge
from app.models.patient import Patient
from app.models.risk_assessment import RiskAssessment
from app.services.escalation_service import acknowledge_escalation, trigger_escalation
from app.services.timeline_service import get_timeline


def _make_triggered_escalation(db):
    patient = Patient(full_name="Demo Patient Ack", synthetic_mrn="SYN-TEST-ACK1", phone_number="+15550003333")
    db.session.add(patient)
    db.session.flush()
    discharge = Discharge(patient_id=patient.id, diagnosis="Test diagnosis")
    db.session.add(discharge)
    db.session.flush()
    call = FollowUpCall(discharge_id=discharge.id, provider_call_id="mock-ack-1", status="completed")
    db.session.add(call)
    db.session.flush()
    assessment = RiskAssessment(call_id=call.id, risk_level="high", score=10, reasons=["Difficulty breathing"])
    db.session.add(assessment)
    db.session.flush()

    escalation = trigger_escalation(assessment)
    return escalation, patient


def test_acknowledge_escalation_transitions_status(app, db):
    escalation, patient = _make_triggered_escalation(db)
    assert escalation.status == "notified"

    updated = acknowledge_escalation(escalation, acknowledged_by="nurse_jane", note="Called patient back, stable")

    assert updated.status == "acknowledged"
    assert updated.acknowledged_by == "nurse_jane"
    assert updated.acknowledgement_note == "Called patient back, stable"
    assert updated.acknowledged_at is not None


def test_acknowledge_escalation_logs_timeline_event(app, db):
    escalation, patient = _make_triggered_escalation(db)
    acknowledge_escalation(escalation, acknowledged_by="nurse_jane")

    events = get_timeline(patient_id=patient.id)
    event_types = {e.event_type for e in events}
    assert "escalation_acknowledged" in event_types


def test_acknowledge_escalation_is_idempotent(app, db):
    escalation, _ = _make_triggered_escalation(db)
    first = acknowledge_escalation(escalation, acknowledged_by="nurse_jane")
    first_ack_time = first.acknowledged_at

    second = acknowledge_escalation(escalation, acknowledged_by="nurse_bob")

    # Calling it again on an already-acknowledged escalation must not
    # overwrite who/when it was first acknowledged.
    assert second.acknowledged_by == "nurse_jane"
    assert second.acknowledged_at == first_ack_time
