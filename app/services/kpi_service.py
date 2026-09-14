"""Calculate dashboard KPIs and the pending follow-up queue.

Queries live here so routes and database tests use the same definitions.
"""
from dataclasses import dataclass
from app.extensions import utcnow

from app.models.call import FollowUpCall
from app.models.discharge import Discharge
from app.models.escalation import EscalationEvent
from app.models.patient import Patient
from app.models.risk_assessment import RiskAssessment


PENDING_FOLLOW_UP_STATUSES = ("pending", "call_scheduled", "needs_review")


@dataclass
class ExecutiveKPIs:
    total_patients: int
    pending_follow_ups: int
    high_risk_patients: int
    escalations_awaiting_acknowledgement: int
    calls_completed_today: int


def get_pending_follow_ups():
    """Operational work queue, including data-quality holds needing review."""
    return (
        Discharge.query.filter(Discharge.status.in_(PENDING_FOLLOW_UP_STATUSES))
        .order_by(Discharge.discharge_date.desc())
        .all()
    )


def compute_kpis() -> ExecutiveKPIs:
    total_patients = Patient.query.count()

    pending_follow_ups = Discharge.query.filter(
        Discharge.status.in_(PENDING_FOLLOW_UP_STATUSES)
    ).count()

    # "High-risk patients" counts distinct patients with at least one
    # high-risk assessment, not raw assessment rows — a patient who's been
    # flagged high risk twice should still count once on an executive KPI.
    high_risk_patient_ids = {
        ra.call.discharge.patient_id
        for ra in RiskAssessment.query.filter_by(risk_level="high").all()
    }
    high_risk_patients = len(high_risk_patient_ids)

    escalations_awaiting_acknowledgement = EscalationEvent.query.filter(
        EscalationEvent.status != "acknowledged"
    ).count()

    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    calls_completed_today = FollowUpCall.query.filter(
        FollowUpCall.status == "completed", FollowUpCall.completed_at >= today_start
    ).count()

    return ExecutiveKPIs(
        total_patients=total_patients,
        pending_follow_ups=pending_follow_ups,
        high_risk_patients=high_risk_patients,
        escalations_awaiting_acknowledgement=escalations_awaiting_acknowledgement,
        calls_completed_today=calls_completed_today,
    )
