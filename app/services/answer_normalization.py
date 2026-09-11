"""
Answer normalization layer — Stage 1 of the CALL-E four-state architecture.

    CALL-E raw recipient_result_schema output
        |
        v
    THIS MODULE (answer_normalization.py)
        |
        v
    4-state semantic answers (NormalizedAnswer)
        |
        v
    orchestration data-quality gate
        |
        +--> complete/valid -> existing clinical risk engine
        +--> incomplete/invalid -> human-review terminal state

This module has exactly one job: take whatever raw dict CALL-E's
`recipient_result_schema` produced (which may be fully present, partially
present, entirely absent, or contain values outside the expected contract)
and convert it into an explicit, auditable, four-state representation —
without ever letting an unknown or invalid value read as reassuring.

This module remains independent of the provider client and clinical risk
engine. The orchestrator consumes its data-quality result before deciding
whether the existing clinical risk path is safe to run.

FIELD-LEVEL SEMANTIC BOUNDARY, stated explicitly per the Stage 1 mandate:
    - For the six binary symptom/compliance fields, this module reuses the
      REASSURING/CONCERNING polarity that risk_engine.py already encodes
      today (e.g. fever="yes" is concerning; medication_taken="yes" is
      reassuring). This is not a new clinical rule — it mirrors an
      already-shipped interpretation, read-only, without modifying
      risk_engine.py itself.
    - For `pain_level`, this module reuses risk_engine.py's existing numeric
      threshold (pain >= 5 is where that file starts adding score).
    - For `general_recovery`, this module enforces the same closed enum sent
      to CALL-E: "improving" and "about the same" are reassuring, "getting
      worse" is concerning, and "unknown" is unavailable. Every other value
      is invalid rather than being guessed from free text.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class AnswerState(Enum):
    """The four required semantic states. No fifth state exists."""

    KNOWN_REASSURING = "known_reassuring"
    KNOWN_CONCERNING = "known_concerning"
    UNKNOWN_UNAVAILABLE = "unknown_unavailable"
    INVALID_UNRECOGNIZED = "invalid_unrecognized"


@dataclass
class NormalizedAnswer:
    """
    One field's normalized representation.

    `raw_value` preserves exactly what was in the incoming dict for this
    key (or None if the key was absent) — the raw CALL-E record is never
    discarded, per the non-negotiable audit invariant.

    `provenance_detail` distinguishes *why* a value landed in its state,
    for audit purposes, even where the risk-facing `state` collapses two
    provenances together (e.g. "field_absent" and "explicit_null" are both
    UNKNOWN_UNAVAILABLE, but remain distinguishable here).
    """

    raw_value: Any
    state: AnswerState
    provenance_detail: str


@dataclass
class ResultQuality:
    """Data-quality result kept separate from clinical risk classification."""

    normalized_answers: Dict[str, NormalizedAnswer]
    field_issues: Dict[str, str]
    top_level_issue: Optional[str] = None

    @property
    def requires_review(self) -> bool:
        return self.top_level_issue is not None or bool(self.field_issues)

    def issue_summary(self) -> str:
        parts = []
        if self.top_level_issue:
            parts.append(self.top_level_issue)
        parts.extend(
            f"{field}:{provenance}"
            for field, provenance in sorted(self.field_issues.items())
        )
        return ", ".join(parts)


# Provenance detail constants — the fixed, closed set this module ever emits.
PROVENANCE_VALID_VALUE = "valid_value"
PROVENANCE_EXPLICIT_UNKNOWN = "explicit_unknown"
PROVENANCE_FIELD_ABSENT = "field_absent"
PROVENANCE_EXPLICIT_NULL = "explicit_null"
PROVENANCE_UNRECOGNIZED_VALUE = "unrecognized_value"


# ---------------------------------------------------------------------------
# Field contract — the 8 CareFlow recovery questions, per the CALL-E
# recipient_result_schema described in the Stage 1 brief. Defined locally
# (not imported from recovery_questions.py) because that module only
# carries prompt text, not the field-kind/polarity information this layer
# needs, and duplicating 8 short key names is a smaller, safer footprint
# than adding a new responsibility to an unrelated existing file.
# ---------------------------------------------------------------------------

# Standard polarity: "yes" means the concerning symptom is present.
_STANDARD_POLARITY_FIELDS = {"fever", "bleeding", "swelling", "difficulty_breathing"}

# Inverted polarity: "yes" means the reassuring compliance behavior happened.
_INVERTED_POLARITY_FIELDS = {"medication_collected", "medication_taken"}

_CATEGORICAL_FIELDS = _STANDARD_POLARITY_FIELDS | _INVERTED_POLARITY_FIELDS
_CATEGORICAL_VALID_VALUES = {"yes", "no"}

_NUMERIC_FIELD = "pain_level"
_NUMERIC_VALID_VALUES = {str(n) for n in range(11)}  # "0".."10"
# Reuses risk_engine.py's existing moderate-risk threshold (pain >= 5 begins
# scoring there) as the reassuring/concerning boundary — see module
# docstring. Not a new threshold; a read-only mirror of an existing one.
_NUMERIC_CONCERNING_THRESHOLD = 5

_GENERAL_RECOVERY_FIELD = "general_recovery"
_GENERAL_RECOVERY_STATES = {
    "improving": AnswerState.KNOWN_REASSURING,
    "about the same": AnswerState.KNOWN_REASSURING,
    "getting worse": AnswerState.KNOWN_CONCERNING,
}

ALL_RECOVERY_FIELDS = _CATEGORICAL_FIELDS | {
    _NUMERIC_FIELD,
    _GENERAL_RECOVERY_FIELD,
}


def _normalize_categorical(key: str, value: Any) -> NormalizedAnswer:
    if value == "unknown":
        return NormalizedAnswer(value, AnswerState.UNKNOWN_UNAVAILABLE, PROVENANCE_EXPLICIT_UNKNOWN)

    if not isinstance(value, str) or value not in _CATEGORICAL_VALID_VALUES:
        # Deliberately strict: the approved contract is string-only
        # ("yes"/"no"/"unknown"). A native bool/int/other value — e.g. the
        # OLD pre-Stage-1 contract's `True`/`False` — is NOT silently
        # coerced. It is flagged as invalid, never treated as reassuring.
        return NormalizedAnswer(value, AnswerState.INVALID_UNRECOGNIZED, PROVENANCE_UNRECOGNIZED_VALUE)

    is_standard = key in _STANDARD_POLARITY_FIELDS
    concerning_value = "yes" if is_standard else "no"
    state = AnswerState.KNOWN_CONCERNING if value == concerning_value else AnswerState.KNOWN_REASSURING
    return NormalizedAnswer(value, state, PROVENANCE_VALID_VALUE)


def _normalize_pain_level(value: Any) -> NormalizedAnswer:
    if value == "unknown":
        return NormalizedAnswer(value, AnswerState.UNKNOWN_UNAVAILABLE, PROVENANCE_EXPLICIT_UNKNOWN)

    if not isinstance(value, str) or value not in _NUMERIC_VALID_VALUES:
        # Strict string-only check — a raw int (old contract) or an
        # out-of-range/non-numeric string is invalid, not coerced.
        return NormalizedAnswer(value, AnswerState.INVALID_UNRECOGNIZED, PROVENANCE_UNRECOGNIZED_VALUE)

    numeric_value = int(value)
    state = (
        AnswerState.KNOWN_CONCERNING
        if numeric_value >= _NUMERIC_CONCERNING_THRESHOLD
        else AnswerState.KNOWN_REASSURING
    )
    return NormalizedAnswer(value, state, PROVENANCE_VALID_VALUE)


def _normalize_general_recovery(value: Any) -> NormalizedAnswer:
    if value == "unknown":
        return NormalizedAnswer(value, AnswerState.UNKNOWN_UNAVAILABLE, PROVENANCE_EXPLICIT_UNKNOWN)

    if not isinstance(value, str) or value not in _GENERAL_RECOVERY_STATES:
        return NormalizedAnswer(value, AnswerState.INVALID_UNRECOGNIZED, PROVENANCE_UNRECOGNIZED_VALUE)

    return NormalizedAnswer(
        value, _GENERAL_RECOVERY_STATES[value], PROVENANCE_VALID_VALUE
    )


def normalize_answer(key: str, raw_answers: Optional[Dict[str, Any]]) -> NormalizedAnswer:
    """
    Normalize a single field from a raw answers dict (which may itself be
    None, entirely absent of this key, or contain this key with value None).

    This is the one function every other case in this module funnels
    through — deliberately kept small enough to read top to bottom.
    """
    if raw_answers is None or key not in raw_answers:
        return NormalizedAnswer(None, AnswerState.UNKNOWN_UNAVAILABLE, PROVENANCE_FIELD_ABSENT)

    value = raw_answers[key]

    if value is None:
        return NormalizedAnswer(None, AnswerState.UNKNOWN_UNAVAILABLE, PROVENANCE_EXPLICIT_NULL)

    if key in _CATEGORICAL_FIELDS:
        return _normalize_categorical(key, value)
    if key == _NUMERIC_FIELD:
        return _normalize_pain_level(value)
    if key == _GENERAL_RECOVERY_FIELD:
        return _normalize_general_recovery(value)

    # A key outside the known 8-field contract entirely. Never silently
    # dropped or treated as reassuring — surfaced as invalid so a future
    # caller can decide what to do with an unexpected field name.
    return NormalizedAnswer(value, AnswerState.INVALID_UNRECOGNIZED, PROVENANCE_UNRECOGNIZED_VALUE)


def normalize_all(raw_answers: Optional[Dict[str, Any]]) -> Dict[str, NormalizedAnswer]:
    """
    Normalize every field in the known 8-field recovery-question contract,
    regardless of what raw_answers actually contains — including the
    `raw_answers is None` case (CALL-E's `structured_result` was null),
    which yields all 8 fields as UNKNOWN_UNAVAILABLE / field_absent rather
    than raising or silently returning an empty result.
    """
    return {field: normalize_answer(field, raw_answers) for field in ALL_RECOVERY_FIELDS}


def assess_result_quality(raw_answers: Any) -> ResultQuality:
    """
    Decide whether a raw structured result is complete and contract-valid.

    Raw values are not rewritten or discarded. The returned normalized map
    carries field state and provenance for the caller's audit/review decision;
    clinical risk scoring remains a separate downstream concern.
    """
    if raw_answers is None:
        normalized = normalize_all(None)
        return ResultQuality(
            normalized_answers=normalized,
            field_issues={
                field: answer.provenance_detail for field, answer in normalized.items()
            },
            top_level_issue="structured_result_absent",
        )

    if not isinstance(raw_answers, dict):
        normalized = normalize_all(None)
        return ResultQuality(
            normalized_answers=normalized,
            field_issues={
                field: answer.provenance_detail for field, answer in normalized.items()
            },
            top_level_issue="structured_result_not_object",
        )

    normalized = normalize_all(raw_answers)
    field_issues = {
        field: answer.provenance_detail
        for field, answer in normalized.items()
        if answer.state
        in {AnswerState.UNKNOWN_UNAVAILABLE, AnswerState.INVALID_UNRECOGNIZED}
    }

    for unexpected_field in set(raw_answers) - ALL_RECOVERY_FIELDS:
        field_issues[unexpected_field] = PROVENANCE_UNRECOGNIZED_VALUE

    return ResultQuality(
        normalized_answers=normalized,
        field_issues=field_issues,
    )
