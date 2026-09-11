"""
TimelineEvent model.

An append-only log of every significant workflow action, scoped optionally
to a patient, discharge, and/or call (whichever apply — a "Patient Created"
event has no discharge/call yet; a "Risk Assessment Generated" event has
all three). This is what powers both the dashboard's chronological feed and
(later) any audit-log requirement, without needing a separate audit system.
"""

from app.extensions import db, utcnow


class TimelineEvent(db.Model):
    __tablename__ = "timeline_events"

    id = db.Column(db.Integer, primary_key=True)

    # Nullable FKs: an event is scoped to whichever entities exist at the
    # time it's logged. No backref/relationship objects are defined here
    # deliberately — timeline events are written far more often than
    # navigated from the parent side, and querying by FK column directly
    # (see timeline_service.get_timeline) is simpler than maintaining four
    # more relationship() declarations across already-busy models.
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)
    discharge_id = db.Column(db.Integer, db.ForeignKey("discharges.id"), nullable=True)
    call_id = db.Column(db.Integer, db.ForeignKey("follow_up_calls.id"), nullable=True)

    # Machine-readable type, e.g. "patient_created", "call_completed".
    # Kept as a free-text column (not an Enum) so new event types can be
    # added by services without a schema migration.
    event_type = db.Column(db.String(50), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_metadata = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return f"<TimelineEvent {self.id} {self.event_type} @ {self.created_at}>"

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "discharge_id": self.discharge_id,
            "call_id": self.call_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "metadata": self.event_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
