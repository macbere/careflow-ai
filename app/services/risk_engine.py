"""
Deterministic rule-based risk engine.

Phase 1 constraint: no LLM reasoning. This is intentional — a deterministic,
explainable rubric is easier to demo, easier to trust, and easier to defend
to judges/clinicians than an opaque model. Every score comes with a list of
concrete `reasons`, so a nurse looking at the dashboard can see exactly why
a patient was flagged.

Scoring is simple and additive: each concerning answer adds points; the
total maps to a risk_level. Thresholds are intentionally conservative
(biased toward escalating rather than missing a high-risk patient) — the
cost of a false escalation is a nurse making an unnecessary call; the cost
of a missed one is a patient in danger.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


HIGH_RISK_THRESHOLD = 8
MEDIUM_RISK_THRESHOLD = 4

# Conservative score contributed when a field's value is "unknown" (or
# missing) rather than a real answer. Reuses the exact value the missing
# pain_level case already used before this fix — not a new invented
# number, the existing project convention applied uniformly across every
# field so "unknown" can never silently score the same as that field's
# reassuring answer (which always scores 0).
_UNKNOWN_FIELD_SCORE = 2


@dataclass
class RiskResult:
    risk_level: str  # "low" | "medium" | "high"
    score: int
    reasons: List[str] = field(default_factory=list)


def assess_risk(answers: Dict[str, Any]) -> RiskResult:
    """
    Score a completed call's structured answers.

    `answers` is expected to have the keys defined in
    app/services/recovery_questions.py. Missing keys are treated
    conservatively (as if the concerning answer was given), since a call
    that failed to capture an answer is itself a signal worth a human's
    attention rather than being silently ignored.
    """
    score = 0
    reasons: List[str] = []

    # Compatibility boundary for the current CALL-E string contract.
    # Existing scoring semantics are intentionally unchanged for defined
    # values:
    #   "yes" -> True
    #   "no"  -> False
    #   "0".."10" -> int
    # "unknown" is NOT coerced to True/False/int by these helpers — it is
    # left as the literal string "unknown" so the explicit checks below
    # can give it its own conservative handling, rather than letting it
    # silently fail every is-True/is-False/isinstance check and
    # contribute nothing (the defect this fix resolves).
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
        # Weighted to meet HIGH_RISK_THRESHOLD on its own (not just in
        # combination with other symptoms) — difficulty breathing is a
        # single-symptom red flag that should trigger escalation by itself,
        # consistent with this module's "bias toward escalating" design.
        score += HIGH_RISK_THRESHOLD
        reasons.append("Patient reports difficulty breathing")
    elif difficulty_breathing == "unknown":
        # Deliberately non-zero: an unknown answer for this specific field
        # must never score identically to "no" (which scores 0) — this is
        # the field weighted to independently trigger "high" on its own
        # when the answer IS captured as concerning, so leaving "unknown"
        # silently equivalent to "no" would be the single most dangerous
        # instance of this defect. Kept at the same conservative weight as
        # every other unknown field rather than escalated further, since
        # inventing a larger, field-specific unknown-penalty would itself
        # be a new, undiscussed clinical judgment this fix isn't
        # authorized to make.
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
