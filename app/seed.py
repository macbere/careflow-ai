"""
Seed the database with fabricated, clearly-synthetic patients and discharges.

Run with: python -m app.seed

Naming convention: every patient is named "Demo Patient N" with a "SYN-"
prefixed MRN and a reserved fictional phone number (555 exchange, never a
real routable US number), so there is no ambiguity that this is not real
health data.
"""
from datetime import timedelta

from app import create_app
from app.extensions import db, logger, utcnow
from app.models.discharge import Discharge
from app.models.patient import Patient
from app.services import timeline_service

SYNTHETIC_PATIENTS = [
    {"full_name": "Demo Patient 1", "synthetic_mrn": "SYN-00001", "phone_number": "+15550000001", "diagnosis": "Appendectomy recovery"},
    {"full_name": "Demo Patient 2", "synthetic_mrn": "SYN-00002", "phone_number": "+15550000002", "diagnosis": "Hip replacement recovery"},
    {"full_name": "Demo Patient 3", "synthetic_mrn": "SYN-00003", "phone_number": "+15550000003", "diagnosis": "Pneumonia treatment"},
    {"full_name": "Demo Patient 4", "synthetic_mrn": "SYN-00004", "phone_number": "+15550000004", "diagnosis": "Cardiac catheterization recovery"},
]


def seed():
    app = create_app()
    with app.app_context():
        if Patient.query.first() is not None:
            logger.info("Database already seeded — skipping.")
            return

        for entry in SYNTHETIC_PATIENTS:
            patient = Patient(
                full_name=entry["full_name"],
                synthetic_mrn=entry["synthetic_mrn"],
                phone_number=entry["phone_number"],
            )
            db.session.add(patient)
            db.session.flush()

            timeline_service.log_event(
                event_type="patient_created",
                title=f"Patient created: {patient.full_name}",
                description=f"Synthetic MRN {patient.synthetic_mrn}",
                patient_id=patient.id,
                commit=False,
            )

            discharge = Discharge(
                patient_id=patient.id,
                diagnosis=entry["diagnosis"],
                discharge_date=utcnow() - timedelta(days=1),
            )
            db.session.add(discharge)
            db.session.flush()

            timeline_service.log_event(
                event_type="patient_discharged",
                title=f"{patient.full_name} discharged",
                description=f"Diagnosis: {entry['diagnosis']}",
                patient_id=patient.id,
                discharge_id=discharge.id,
                commit=False,
            )

        db.session.commit()
        logger.info("Seeded %d synthetic patients with discharges.", len(SYNTHETIC_PATIENTS))


if __name__ == "__main__":
    seed()
