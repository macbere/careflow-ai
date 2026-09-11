"""
Tests for app/services/answer_normalization.py — Stage 1 only.

This module has zero dependency on Flask/SQLAlchemy/risk_engine.py/
call_orchestrator.py, so these tests are runnable standalone without the
app's database/web stack, and are runnable via plain pytest.
"""
import pytest

from app.services.answer_normalization import (
    AnswerState,
    PROVENANCE_EXPLICIT_NULL,
    PROVENANCE_EXPLICIT_UNKNOWN,
    PROVENANCE_FIELD_ABSENT,
    PROVENANCE_UNRECOGNIZED_VALUE,
    PROVENANCE_VALID_VALUE,
    normalize_all,
    normalize_answer,
)


# --- A. Valid reassuring categorical value ---------------------------------

def test_a_valid_reassuring_categorical_standard_polarity():
    result = normalize_answer("fever", {"fever": "no"})
    assert result.state == AnswerState.KNOWN_REASSURING
    assert result.provenance_detail == PROVENANCE_VALID_VALUE
    assert result.raw_value == "no"


def test_a_valid_reassuring_categorical_inverted_polarity():
    # medication_taken="yes" is REASSURING (inverted polarity)
    result = normalize_answer("medication_taken", {"medication_taken": "yes"})
    assert result.state == AnswerState.KNOWN_REASSURING


# --- B. Valid concerning categorical value ----------------------------------

def test_b_valid_concerning_categorical_standard_polarity():
    result = normalize_answer("difficulty_breathing", {"difficulty_breathing": "yes"})
    assert result.state == AnswerState.KNOWN_CONCERNING
    assert result.provenance_detail == PROVENANCE_VALID_VALUE


def test_b_valid_concerning_categorical_inverted_polarity():
    # medication_collected="no" is CONCERNING (inverted polarity)
    result = normalize_answer("medication_collected", {"medication_collected": "no"})
    assert result.state == AnswerState.KNOWN_CONCERNING


# --- C. Explicit "unknown" ---------------------------------------------------

def test_c_explicit_unknown_categorical():
    result = normalize_answer("fever", {"fever": "unknown"})
    assert result.state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result.provenance_detail == PROVENANCE_EXPLICIT_UNKNOWN


# --- D. Missing field ---------------------------------------------------

def test_d_missing_field():
    result = normalize_answer("bleeding", {"fever": "no"})  # bleeding key absent
    assert result.state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result.provenance_detail == PROVENANCE_FIELD_ABSENT
    assert result.raw_value is None


# --- E. Explicit null ---------------------------------------------------

def test_e_explicit_null():
    result = normalize_answer("swelling", {"swelling": None})
    assert result.state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result.provenance_detail == PROVENANCE_EXPLICIT_NULL


# --- F. Invalid/unrecognized value ---------------------------------------------------

def test_f_invalid_unrecognized_categorical():
    result = normalize_answer("fever", {"fever": "maybe"})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED
    assert result.provenance_detail == PROVENANCE_UNRECOGNIZED_VALUE
    # Critical: never silently reassuring
    assert result.state != AnswerState.KNOWN_REASSURING


def test_f_old_contract_boolean_is_invalid_not_coerced():
    """
    The pre-Stage-1 contract used native Python booleans. Under the new
    string-only contract, a stray True/False must be flagged invalid, not
    silently treated as a valid yes/no — this is the exact compatibility
    gap IMPLEMENTATION_READINESS_AUDIT.md identified in risk_engine.py.
    """
    result = normalize_answer("fever", {"fever": True})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED


# --- G. Valid pain values ---------------------------------------------------

def test_g_valid_pain_reassuring_low():
    result = normalize_answer("pain_level", {"pain_level": "2"})
    assert result.state == AnswerState.KNOWN_REASSURING
    assert result.provenance_detail == PROVENANCE_VALID_VALUE


def test_g_valid_pain_concerning_high():
    result = normalize_answer("pain_level", {"pain_level": "8"})
    assert result.state == AnswerState.KNOWN_CONCERNING


def test_g_valid_pain_boundary_at_threshold():
    # Threshold is >= 5 concerning, per module docstring (mirrors
    # risk_engine.py's existing moderate-risk boundary)
    assert normalize_answer("pain_level", {"pain_level": "4"}).state == AnswerState.KNOWN_REASSURING
    assert normalize_answer("pain_level", {"pain_level": "5"}).state == AnswerState.KNOWN_CONCERNING


def test_g_valid_pain_zero():
    result = normalize_answer("pain_level", {"pain_level": "0"})
    assert result.state == AnswerState.KNOWN_REASSURING


def test_g_valid_pain_ten():
    result = normalize_answer("pain_level", {"pain_level": "10"})
    assert result.state == AnswerState.KNOWN_CONCERNING


# --- H. Pain "unknown" ---------------------------------------------------

def test_h_pain_unknown():
    result = normalize_answer("pain_level", {"pain_level": "unknown"})
    assert result.state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result.provenance_detail == PROVENANCE_EXPLICIT_UNKNOWN
    # Regression guard for the exact live-validated scenario:
    # pain_level="unknown" must NEVER become reassuring.
    assert result.state != AnswerState.KNOWN_REASSURING


# --- I. Invalid pain value ---------------------------------------------------

def test_i_invalid_pain_out_of_range():
    result = normalize_answer("pain_level", {"pain_level": "11"})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED


def test_i_invalid_pain_negative():
    result = normalize_answer("pain_level", {"pain_level": "-1"})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED


def test_i_invalid_pain_non_numeric_string():
    result = normalize_answer("pain_level", {"pain_level": "a little"})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED
    # Critical: no natural-language guessing — "a little" must never
    # become a specific number like 2.
    assert result.raw_value == "a little"


def test_i_invalid_pain_old_contract_native_int():
    # Old contract sent a native int, e.g. 2. New contract is string-only.
    result = normalize_answer("pain_level", {"pain_level": 2})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED


# --- J. Closed general-recovery contract -----------------------------------

@pytest.mark.parametrize(
    ("value", "expected_state", "expected_provenance"),
    [
        ("improving", AnswerState.KNOWN_REASSURING, PROVENANCE_VALID_VALUE),
        ("about the same", AnswerState.KNOWN_REASSURING, PROVENANCE_VALID_VALUE),
        ("getting worse", AnswerState.KNOWN_CONCERNING, PROVENANCE_VALID_VALUE),
        ("unknown", AnswerState.UNKNOWN_UNAVAILABLE, PROVENANCE_EXPLICIT_UNKNOWN),
    ],
)
def test_j_general_recovery_allowed_values(
    value, expected_state, expected_provenance
):
    result = normalize_answer("general_recovery", {"general_recovery": value})

    assert result.state == expected_state
    assert result.provenance_detail == expected_provenance
    assert result.raw_value == value


@pytest.mark.parametrize(
    "value",
    [
        "terrible",
        "declining",
        "not improving",
        "worsening",
        "stable",
        "",
        "IMPROVING",
        123,
        True,
    ],
)
def test_j_general_recovery_rejects_every_out_of_contract_value(value):
    result = normalize_answer("general_recovery", {"general_recovery": value})

    assert result.state == AnswerState.INVALID_UNRECOGNIZED
    assert result.state != AnswerState.KNOWN_REASSURING
    assert result.provenance_detail == PROVENANCE_UNRECOGNIZED_VALUE
    assert result.raw_value == value


def test_j_general_recovery_explicit_null_remains_unavailable():
    result = normalize_answer("general_recovery", {"general_recovery": None})

    assert result.state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result.provenance_detail == PROVENANCE_EXPLICIT_NULL


# --- K. Unexpected data type ---------------------------------------------------

def test_k_unexpected_type_list():
    result = normalize_answer("fever", {"fever": ["no"]})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED


def test_k_unexpected_type_dict():
    result = normalize_answer("pain_level", {"pain_level": {"value": 2}})
    assert result.state == AnswerState.INVALID_UNRECOGNIZED


# --- L. Empty structured result ---------------------------------------------------

def test_l_empty_dict_all_fields_unavailable():
    result = normalize_all({})
    assert len(result) == 8
    assert all(a.state == AnswerState.UNKNOWN_UNAVAILABLE for a in result.values())
    assert all(a.provenance_detail == PROVENANCE_FIELD_ABSENT for a in result.values())


# --- M. Entire structured_result = None ---------------------------------------------------

def test_m_entire_structured_result_none():
    result = normalize_all(None)
    assert len(result) == 8
    assert all(a.state == AnswerState.UNKNOWN_UNAVAILABLE for a in result.values())
    # Never reassuring, regardless of field
    assert not any(a.state == AnswerState.KNOWN_REASSURING for a in result.values())


# --- N. Mixed known + unknown answers ---------------------------------------------------

def test_n_mixed_known_and_unknown():
    raw = {
        "pain_level": "unknown",
        "fever": "no",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "no",
        "general_recovery": "improving",
    }
    result = normalize_all(raw)
    assert result["pain_level"].state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result["fever"].state == AnswerState.KNOWN_REASSURING
    assert result["general_recovery"].state == AnswerState.KNOWN_REASSURING


# --- O. Known concerning + unknown answers ---------------------------------------------------

def test_o_concerning_answer_survives_alongside_unknowns():
    raw = {
        "pain_level": "unknown",
        "fever": "unknown",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "yes",  # genuinely concerning, captured clearly
        "general_recovery": "improving",
    }
    result = normalize_all(raw)
    # The one captured concerning answer must remain concerning — this is
    # non-negotiable safety invariant #9.
    assert result["difficulty_breathing"].state == AnswerState.KNOWN_CONCERNING
    assert result["pain_level"].state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result["fever"].state == AnswerState.UNKNOWN_UNAVAILABLE


# --- Regression test: the original live failure pattern ---------------------

def test_regression_seven_clear_one_unavailable_never_becomes_all_clear():
    """
    Direct regression test for the exact pattern from the original live
    validation call (call_B8kZIifzoZ0pCdPIUhuciA / DESIGN_DECISION_REPORT.md):
    7 answers clearly reassuring, 1 answer (pain) unavailable.

    The normalized output must preserve pain_level as UNKNOWN_UNAVAILABLE.
    It must NEVER present as an all-reassuring/all-clear state.
    """
    raw = {
        "fever": "no",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "no",
        "general_recovery": "improving",
        # pain_level deliberately absent — mirrors the real call exactly
    }
    result = normalize_all(raw)

    assert result["pain_level"].state == AnswerState.UNKNOWN_UNAVAILABLE
    assert result["pain_level"].provenance_detail == PROVENANCE_FIELD_ABSENT

    # The other 7 are genuinely, correctly reassuring
    for key in ("fever", "medication_collected", "medication_taken", "bleeding", "swelling", "difficulty_breathing", "general_recovery"):
        assert result[key].state == AnswerState.KNOWN_REASSURING, f"{key} should be reassuring"

    # The overall answer set is NOT uniformly reassuring — this is the
    # property a future risk/completeness layer depends on to avoid the
    # original silent-low-risk bug.
    states = {a.state for a in result.values()}
    assert AnswerState.UNKNOWN_UNAVAILABLE in states
    assert states != {AnswerState.KNOWN_REASSURING}
