"""Generate and store a care summary from a completed call.

The current generator uses structured answers and the stored assessment.
It makes no model calls. CareSummaryGenerator defines the interface for
summary implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from app.extensions import db, logger
from app.models.call import FollowUpCall
from app.models.care_summary import CareSummary


@dataclass
class CareSummaryData:
    """Provider-agnostic summary output — what any generator must produce."""

    patient_name: str
    discharge_diagnosis: str
    recovery_status: str
    symptoms_reported: List[str] = field(default_factory=list)
    risk_score: int = 0
    risk_reasons: List[str] = field(default_factory=list)
    recommended_next_step: str = ""
    escalation_status: str = "none"
    generated_by: str = "deterministic_v1"


class CareSummaryGenerator(ABC):
    """Abstract interface every summary generator (deterministic or LLM) implements."""

    @abstractmethod
    def generate(self, call: FollowUpCall) -> CareSummaryData:
        raise NotImplementedError


# Rule-based recommendation text, one per risk level. Kept as a simple
# mapping (not embedded in risk_engine.py) because "what to recommend" is a
# care-summary/product concern, while risk_engine.py's job is purely scoring.
_NEXT_STEP_BY_RISK_LEVEL = {
    "high": "Immediate nurse review required; escalation has been triggered and a callback should occur within 1 hour.",
    "medium": "Schedule a follow-up call within 48 hours and monitor reported symptoms.",
    "low": "No immediate action needed. Continue routine follow-up per the standard care plan.",
}

_ANSWER_KEY_TO_SYMPTOM_LABEL = {
    "fever": "Fever reported",
    "bleeding": "Unexpected bleeding reported",
    "swelling": "Unusual swelling reported",
    "difficulty_breathing": "Difficulty breathing reported",
}


class DeterministicCareSummaryGenerator(CareSummaryGenerator):
    """Build a reproducible summary from stored answers and assessment data."""

    def generate(self, call: FollowUpCall) -> CareSummaryData:
        answers = call.structured_answers or {}
        assessment = call.risk_assessment
        patient = call.discharge.patient

        # Compatibility with both the legacy native-Python answer format
        # (True/False/int) and the current CALL-E string contract
        # ("yes"/"no" and "0".."10"). Unknown/unrecognized values are
        # deliberately left unresolved rather than treated as reassuring.
        def _bool_value(value):
            if value == "yes":
                return True
            if value == "no":
                return False
            return value

        def _pain_value(value):
            if isinstance(value, str) and value in {str(n) for n in range(11)}:
                return int(value)
            return value

        symptoms = [
            label
            for key, label in _ANSWER_KEY_TO_SYMPTOM_LABEL.items()
            if _bool_value(answers.get(key)) is True
        ]

        symptom_answer_unavailable = any(
            _bool_value(answers.get(key)) not in (True, False)
            for key in _ANSWER_KEY_TO_SYMPTOM_LABEL
        )

        pain_level = _pain_value(answers.get("pain_level"))
        if isinstance(pain_level, (int, float)):
            if pain_level >= 5:
                symptoms.append(f"Pain level {pain_level}/10")
        else:
            symptom_answer_unavailable = True

        if not symptoms:
            if symptom_answer_unavailable:
                symptoms.append("Some symptom responses were unavailable")
            else:
                symptoms.append("No concerning symptoms reported")

        recovery_status = str(answers.get("general_recovery", "unknown")) or "unknown"

        risk_level = assessment.risk_level if assessment else "unknown"
        risk_score = assessment.score if assessment else 0
        risk_reasons = assessment.reasons if assessment else []

        escalation_status = "none"
        if assessment and assessment.escalation:
            escalation_status = assessment.escalation.status

        return CareSummaryData(
            patient_name=patient.full_name,
            discharge_diagnosis=call.discharge.diagnosis,
            recovery_status=recovery_status,
            symptoms_reported=symptoms,
            risk_score=risk_score,
            risk_reasons=risk_reasons,
            recommended_next_step=_NEXT_STEP_BY_RISK_LEVEL.get(
                risk_level, "Review call transcript to determine next step."
            ),
            escalation_status=escalation_status,
            generated_by="deterministic_v1",
        )


def generate_and_store_summary(
    call: FollowUpCall, generator: CareSummaryGenerator = None
) -> CareSummary:
    """
    Generate a CareSummary for a completed call and persist it.

    Call this only after a call has both structured_answers and a
    risk_assessment — the orchestrator enforces that ordering.
    """
    generator = generator or DeterministicCareSummaryGenerator()
    data = generator.generate(call)

    summary = CareSummary.query.filter_by(call_id=call.id).first()
    if summary is None:
        summary = CareSummary(call_id=call.id)
        db.session.add(summary)

    # Upsert in place: a replay repairs a partially completed workflow (for
    # example a summary created before escalation finished) without creating
    # a second summary row.
    summary.patient_name = data.patient_name
    summary.discharge_diagnosis = data.discharge_diagnosis
    summary.recovery_status = data.recovery_status
    summary.symptoms_reported = data.symptoms_reported
    summary.risk_score = data.risk_score
    summary.risk_reasons = data.risk_reasons
    summary.recommended_next_step = data.recommended_next_step
    summary.escalation_status = data.escalation_status
    summary.generated_by = data.generated_by
    db.session.flush()

    logger.info("Care summary generated for call %s (generator=%s)", call.id, data.generated_by)
    return summary
