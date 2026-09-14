"""Score structured recovery answers with the prototype's additive rubric.

Each score includes reasons for review. The orchestrator checks result
quality first and sends incomplete or unknown answers to needs_review.
The thresholds are demonstration rules, not a validated clinical scale.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


HIGH_RISK_THRESHOLD = 8
MEDIUM_RISK_THRESHOLD = 4

# Legacy fallback weight for explicit unknown answers. The application
# quality gate routes these results to review before scoring.
_UNKNOWN_FIELD_SCORE = 2


@dataclass
class RiskResult:
    risk_level: str  # "low" | "medium" | "high"
    score: int
    reasons: List[str] = field(default_factory=list)


def assess_risk(answers: Dict[str, Any]) -> RiskResult:
    """Score recovery answers after the application's result-quality check.

    Expected fields are defined in recovery_questions.py. Direct callers
    can also exercise the legacy unknown-value fallbacks below.
    """
    score = 0
    reasons: List[str] = []

    # CALL-E returns yes/no and numeric strings. Preserve unknown values
    # for the fallback checks below.
    def _bool_value(value: Any) -> Any:
        if value == "yes":
            return True
        if value == "no":
            return False
        return value

    def _pain_value(value: Any) -> Any:
        if isinstance(value, str) and value in {str(n) for n in range(11)}:
            return int(value)
        return value

    pain_level = _pain_value(answers.get("pain_level"))
    if pain_level is None or pain_level == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Pain level was not captured during the call")
    elif isinstance(pain_level, (int, float)):
        if pain_level >= 8:
            score += 5
            reasons.append(f"Pain level {pain_level}/10 is severe")
        elif pain_level >= 5:
            score += 2
            reasons.append(f"Pain level {pain_level}/10 is moderate")

    fever = _bool_value(answers.get("fever"))
    if fever is True:
        score += 3
        reasons.append("Patient reports fever")
    elif fever == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Fever status was not captured during the call")

    difficulty_breathing = _bool_value(answers.get("difficulty_breathing"))
    if difficulty_breathing is True:
        # A known breathing concern reaches the high-risk threshold alone.
        score += HIGH_RISK_THRESHOLD
        reasons.append("Patient reports difficulty breathing")
    elif difficulty_breathing == "unknown":
        # Keep an unknown response distinct from a reassuring no.
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Difficulty breathing status was not captured during the call")

    bleeding = _bool_value(answers.get("bleeding"))
    if bleeding is True:
        score += 4
        reasons.append("Patient reports unexpected bleeding")
    elif bleeding == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Bleeding status was not captured during the call")

    swelling = _bool_value(answers.get("swelling"))
    if swelling is True:
        score += 2
        reasons.append("Patient reports unusual swelling")
    elif swelling == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Swelling status was not captured during the call")

    medication_collected = _bool_value(answers.get("medication_collected"))
    if medication_collected is False:
        score += 3
        reasons.append("Patient was not able to collect prescribed medication")
    elif medication_collected == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Medication collection status was not captured during the call")

    medication_taken = _bool_value(answers.get("medication_taken"))
    if medication_taken is False:
        score += 2
        reasons.append("Patient has not been taking medication as prescribed")
    elif medication_taken == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("Medication adherence status was not captured during the call")

    general_recovery_raw = answers.get("general_recovery")
    if general_recovery_raw == "unknown":
        score += _UNKNOWN_FIELD_SCORE
        reasons.append("General recovery description was not captured during the call")
    else:
        general_recovery = str(general_recovery_raw or "").lower()
        if "worse" in general_recovery or "worsening" in general_recovery:
            score += 3
            reasons.append("Patient describes their recovery as getting worse")

    if score >= HIGH_RISK_THRESHOLD:
        risk_level = "high"
    elif score >= MEDIUM_RISK_THRESHOLD:
        risk_level = "medium"
    else:
        risk_level = "low"

    if not reasons:
        reasons.append("No concerning factors reported during the call")

    return RiskResult(risk_level=risk_level, score=score, reasons=reasons)
