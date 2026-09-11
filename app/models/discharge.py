"""Discharge model — represents a single hospital discharge event for a patient."""
from app.extensions import db, utcnow


class Discharge(db.Model):
    __tablename__ = "discharges"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)

    diagnosis = db.Column(db.String(200), nullable=False)
    discharge_date = db.Column(db.DateTime, default=utcnow, nullable=False)

    # High-level lifecycle status for this discharge's follow-up process.
    # pending -> call_scheduled -> call_completed -> closed
    status = db.Column(db.String(30), default="pending", nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow)

    patient = db.relationship("Patient", back_populates="discharges")
    calls = db.relationship(
        "FollowUpCall", back_populates="discharge", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Discharge {self.id} patient={self.patient_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "diagnosis": self.diagnosis,
            "discharge_date": self.discharge_date.isoformat() if self.discharge_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
