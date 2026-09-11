"""
Patient model.

IMPORTANT: This application is seeded exclusively with synthetic patients
(see app/seed.py). Do not connect this model to any real patient data source.
"""

from app.extensions import db, utcnow


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)

    # Synthetic-data convention: names are drawn from a fabricated pool and
    # MRNs use a "SYN-" prefix so it's unmistakable that this isn't real PHI.
    full_name = db.Column(db.String(120), nullable=False)
    synthetic_mrn = db.Column(db.String(30), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow)

    discharges = db.relationship(
        "Discharge", back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Patient {self.id} {self.full_name} ({self.synthetic_mrn})>"

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "synthetic_mrn": self.synthetic_mrn,
            "phone_number": self.phone_number,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
