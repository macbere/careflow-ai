"""
CareSummary model.

One structured summary per completed call, generated deterministically by
app/services/care_summary.py immediately after risk assessment. Persisted
(rather than computed on every page load) so it has a stable `generated_at`
and so a future LLM-based generator can later overwrite/augment a specific
row without changing how it's displayed.
"""

from app.extensions import db, utcnow


class CareSummary(db.Model):
    __tablename__ = "care_summaries"

    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(
        db.Integer, db.ForeignKey("follow_up_calls.id"), unique=True, nullable=False
    )

    patient_name = db.Column(db.String(120), nullable=False)
    discharge_diagnosis = db.Column(db.String(200), nullable=False)
    recovery_status = db.Column(db.String(50), nullable=False)  # e.g. "improving", "stable", "worsening"

    # List of human-readable symptom strings, e.g. ["Fever reported", "Pain level 8/10"]
    symptoms_reported = db.Column(db.JSON, nullable=False, default=list)

    risk_score = db.Column(db.Integer, nullable=False)
    risk_reasons = db.Column(db.JSON, nullable=False, default=list)

    recommended_next_step = db.Column(db.String(300), nullable=False)
    escalation_status = db.Column(db.String(30), nullable=False)  # "none" | "triggered" | "notified"

    # Which generator produced this summary — lets the dashboard (and any
    # future analytics) distinguish deterministic vs. LLM-generated
    # summaries once that generator exists, without a schema change.
    generated_by = db.Column(db.String(50), nullable=False, default="deterministic_v1")

    generated_at = db.Column(db.DateTime, default=utcnow)

    call = db.relationship("FollowUpCall", backref=db.backref("care_summary", uselist=False))

    def __repr__(self):
        return f"<CareSummary {self.id} call={self.call_id} status={self.recovery_status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "call_id": self.call_id,
            "patient_name": self.patient_name,
            "discharge_diagnosis": self.discharge_diagnosis,
            "recovery_status": self.recovery_status,
            "symptoms_reported": self.symptoms_reported,
            "risk_score": self.risk_score,
            "risk_reasons": self.risk_reasons,
            "recommended_next_step": self.recommended_next_step,
            "escalation_status": self.escalation_status,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
