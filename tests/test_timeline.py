from app.models.patient import Patient
from app.services import timeline_service


def test_log_event_persists_and_is_queryable(app, db):
    patient = Patient(full_name="Demo Patient T", synthetic_mrn="SYN-TEST-4", phone_number="+15550006666")
    db.session.add(patient)
    db.session.flush()

    timeline_service.log_event(
        event_type="patient_created",
        title="Patient created: Demo Patient T",
        patient_id=patient.id,
    )
    timeline_service.log_event(
        event_type="patient_discharged",
        title="Demo Patient T discharged",
        patient_id=patient.id,
    )

    events = timeline_service.get_timeline(patient_id=patient.id)

    assert len(events) == 2
    # Chronological order — oldest first
    assert events[0].event_type == "patient_created"
    assert events[1].event_type == "patient_discharged"


def test_get_timeline_without_patient_id_returns_all(app, db):
    patient = Patient(full_name="Demo Patient U", synthetic_mrn="SYN-TEST-5", phone_number="+15550005555")
    db.session.add(patient)
    db.session.flush()

    timeline_service.log_event(event_type="patient_created", title="x", patient_id=patient.id)

    events = timeline_service.get_timeline()
    assert len(events) >= 1
