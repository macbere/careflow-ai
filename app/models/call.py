"""FollowUpCall model — represents one CALL-E follow-up call attempt and its outcome."""

from app.extensions import db, utcnow


class FollowUpCall(db.Model):
    __tablename__ = "follow_up_calls"

    id = db.Column(db.Integer, primary_key=True)
    discharge_id = db.Column(db.Integer, db.ForeignKey("discharges.id"), nullable=False)

    # Identifier assigned by the voice provider (CALL-E call ID, or a mock ID
    # in local/demo mode). Used to correlate inbound webhooks to this row.
    provider_call_id = db.Column(db.String(100), unique=True, nullable=True)

    # initiated -> in_progress -> completed -> failed / no_answer
    status = db.Column(db.String(30), default="initiated", nullable=False)

    initiated_at = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Raw structured answers captured from the call, stored as JSON.
    # Example shape:
    # {"pain_level": 7, "fever": true, "medication_collected": true,
    #  "medication_taken": true, "bleeding": false, "swelling": false,
    #  "difficulty_breathing": false, "general_recovery": "improving"}
    structured_answers = db.Column(db.JSON, nullable=True)

    transcript = db.Column(db.Text, nullable=True)
    failure_reason = db.Column(db.String(200), nullable=True)

    discharge = db.relationship("Discharge", back_populates="calls")
    risk_assessment = db.relationship(
        "RiskAssessment",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<FollowUpCall {self.id} discharge={self.discharge_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "discharge_id": self.discharge_id,
            "provider_call_id": self.provider_call_id,
            "status": self.status,
            "initiated_at": self.initiated_at.isoformat() if self.initiated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "structured_answers": self.structured_answers,
            "failure_reason": self.failure_reason,
        }
