from app.models.discharge import Discharge
from app.models.patient import Patient


def test_patient_discharge_relationship(app, db):
    patient = Patient(full_name="Demo Patient X", synthetic_mrn="SYN-TEST-1", phone_number="+15550009999")
    db.session.add(patient)
    db.session.flush()

    discharge = Discharge(patient_id=patient.id, diagnosis="Test diagnosis")
    db.session.add(discharge)
    db.session.commit()

    assert len(patient.discharges) == 1
    assert patient.discharges[0].diagnosis == "Test diagnosis"
    assert discharge.status == "pending"
