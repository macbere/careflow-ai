from app.services.risk_engine import assess_risk


def test_low_risk_all_clear_answers():
    answers = {
        "pain_level": 2,
        "fever": False,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": False,
        "general_recovery": "improving",
    }
    result = assess_risk(answers)
    assert result.risk_level == "low"


def test_high_risk_difficulty_breathing_alone_escalates():
    answers = {
        "pain_level": 3,
        "fever": False,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": True,
        "general_recovery": "improving",
    }
    result = assess_risk(answers)
    assert result.risk_level == "high"
    assert any("breathing" in reason.lower() for reason in result.reasons)


def test_high_risk_combination_of_moderate_factors():
    answers = {
        "pain_level": 9,
        "fever": True,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": False,
        "general_recovery": "improving",
    }
    result = assess_risk(answers)
    assert result.risk_level == "high"


def test_medium_risk_moderate_pain_and_fever():
    answers = {
        "pain_level": 6,
        "fever": True,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": False,
        "general_recovery": "about the same",
    }
    result = assess_risk(answers)
    assert result.risk_level == "medium"


def test_missing_pain_level_is_treated_conservatively():
    answers = {
        "fever": False,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": False,
        "general_recovery": "improving",
    }
    result = assess_risk(answers)
    assert any("not captured" in reason.lower() for reason in result.reasons)


# Regression coverage: legacy string conversion once let unknown answers
# score like reassuring ones. These direct scorer tests keep unknown values
# distinct; the orchestrator quality gate handles them before normal scoring.

def _all_reassuring_string_answers():
    return {
        "pain_level": "2",
        "fever": "no",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "no",
        "general_recovery": "improving",
    }


def test_pain_level_unknown_is_not_silently_reassuring():
    answers = _all_reassuring_string_answers()
    answers["pain_level"] = "unknown"
    result = assess_risk(answers)
    assert result.score > 0
    assert any("not captured" in r.lower() for r in result.reasons)


def test_fever_unknown_is_not_silently_reassuring():
    answers = _all_reassuring_string_answers()
    answers["fever"] = "unknown"
    result = assess_risk(answers)
    assert result.score > 0
    assert any("fever" in r.lower() and "not captured" in r.lower() for r in result.reasons)


def test_difficulty_breathing_unknown_is_not_silently_reassuring():
    answers = _all_reassuring_string_answers()
    answers["difficulty_breathing"] = "unknown"
    result = assess_risk(answers)
    assert result.score > 0
    assert any("breathing" in r.lower() and "not captured" in r.lower() for r in result.reasons)


def test_difficulty_breathing_unknown_differs_from_no():
    """
    The critical regression case: difficulty_breathing is the one field
    weighted to independently trigger HIGH risk. "unknown" for this field
    must never score identically to "no" (the reassuring answer).
    """
    answers_no = _all_reassuring_string_answers()
    answers_no["difficulty_breathing"] = "no"

    answers_unknown = _all_reassuring_string_answers()
    answers_unknown["difficulty_breathing"] = "unknown"

    result_no = assess_risk(answers_no)
    result_unknown = assess_risk(answers_unknown)

    assert result_no.score == 0
    assert result_unknown.score > result_no.score


def test_known_reassuring_categorical_values_still_score_zero():
    """Confirms the fix didn't change behavior for defined 'no' answers."""
    result = assess_risk(_all_reassuring_string_answers())
    assert result.score == 0
    assert result.risk_level == "low"


def test_difficulty_breathing_yes_still_independently_high():
    """Confirms the fix preserved the existing HIGH-risk red flag behavior."""
    answers = _all_reassuring_string_answers()
    answers["difficulty_breathing"] = "yes"
    result = assess_risk(answers)
    assert result.risk_level == "high"


def test_pain_level_string_nine_still_scores_as_severe():
    """Confirms the fix preserved existing numeric-string pain scoring."""
    answers = _all_reassuring_string_answers()
    answers["pain_level"] = "9"
    result = assess_risk(answers)
    assert any("severe" in r.lower() for r in result.reasons)


def test_general_recovery_unknown_is_not_silently_reassuring():
    answers = _all_reassuring_string_answers()
    answers["general_recovery"] = "unknown"
    result = assess_risk(answers)
    assert result.score > 0
    assert any("not captured" in r.lower() for r in result.reasons)
