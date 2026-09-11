"""
Models package.

Every model must be imported here so that `db.create_all()` (called from the
application factory) knows about all tables. Forgetting to import a new model
here is a common source of "table doesn't exist" bugs.
"""
from app.models.patient import Patient
from app.models.discharge import Discharge
from app.models.call import FollowUpCall
from app.models.risk_assessment import RiskAssessment
from app.models.escalation import EscalationEvent
from app.models.timeline_event import TimelineEvent
from app.models.care_summary import CareSummary

__all__ = [
    "Patient",
    "Discharge",
    "FollowUpCall",
    "RiskAssessment",
    "EscalationEvent",
    "TimelineEvent",
    "CareSummary",
]
