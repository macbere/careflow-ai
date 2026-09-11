"""RiskAssessment model — output of the risk engine for a completed call."""

from app.extensions import db, utcnow


class RiskAssessment(db.Model):
    __tablename__ = "risk_assessments"

    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(
        db.Integer, db.ForeignKey("follow_up_calls.id"), unique=True, nullable=False
    )

    # "low" | "medium" | "high"
    risk_level = db.Column(db.String(10), nullable=False)

    # Numeric score for sorting/dashboarding; the *level* is what drives
    # workflow decisions, the score is supporting detail.
    score = db.Column(db.Integer, nullable=False)

    # Human-readable list of which factors drove the score, e.g.
    # ["Pain level 9/10 exceeds high-risk threshold", "Reports fever"]
    reasons = db.Column(db.JSON, nullable=False, default=list)

    assessed_at = db.Column(db.DateTime, default=utcnow)

    call = db.relationship("FollowUpCall", back_populates="risk_assessment")
    escalation = db.relationship(
        "EscalationEvent",
        back_populates="risk_assessment",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<RiskAssessment {self.id} call={self.call_id} level={self.risk_level}>"

    def to_dict(self):
        return {
            "id": self.id,
            "call_id": self.call_id,
            "risk_level": self.risk_level,
            "score": self.score,
            "reasons": self.reasons,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
        }
