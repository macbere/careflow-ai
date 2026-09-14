"""EscalationEvent model — records that a high-risk assessment triggered escalation."""

from app.extensions import db, utcnow


class EscalationEvent(db.Model):
    __tablename__ = "escalation_events"

    id = db.Column(db.Integer, primary_key=True)
    risk_assessment_id = db.Column(
        db.Integer, db.ForeignKey("risk_assessments.id"), unique=True, nullable=False
    )

    # triggered -> notified -> acknowledged; notified currently means logged.
    status = db.Column(db.String(20), default="triggered", nullable=False)

    # Delivery detail from the notification adapter; currently a log entry.
    action_taken = db.Column(db.String(120), nullable=True)

    triggered_at = db.Column(db.DateTime, default=utcnow)
    notified_at = db.Column(db.DateTime, nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.String(120), nullable=True)
    acknowledgement_note = db.Column(db.String(300), nullable=True)

    risk_assessment = db.relationship("RiskAssessment", back_populates="escalation")

    def __repr__(self):
        return f"<EscalationEvent {self.id} assessment={self.risk_assessment_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "risk_assessment_id": self.risk_assessment_id,
            "status": self.status,
            "action_taken": self.action_taken,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "acknowledgement_note": self.acknowledgement_note,
        }
