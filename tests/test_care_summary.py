from app.models.call import FollowUpCall
from app.models.discharge import Discharge
from app.models.patient import Patient
from app.models.risk_assessment import RiskAssessment
from app.services.care_summary import DeterministicCareSummaryGenerator, generate_and_store_summary


def _make_completed_call(db, answers, risk_level="low", score=0, reasons=None):
    patient = Patient(full_name="Demo Patient Z", synthetic_mrn="SYN-TEST-3", phone_number="+15550007777")
    db.session.add(patient)
    db.session.flush()

    discharge = Discharge(patient_id=patient.id, diagnosis="Test procedure")
    db.session.add(discharge)
    db.session.flush()

    call = FollowUpCall(
        discharge_id=discharge.id,
        provider_call_id="mock-test-1",
        status="completed",
        structured_answers=answers,
    )
    db.session.add(call)
    db.session.flush()

    assessment = RiskAssessment(call_id=call.id, risk_level=risk_level, score=score, reasons=reasons or [])
    db.session.add(assessment)
    db.session.flush()

    return call


def test_deterministic_summary_reflects_symptoms_and_recommendation(app, db):
    answers = {
        "pain_level": 9,
        "fever": True,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": False,
        "general_recovery": "getting worse",
    }
    call = _make_completed_call(db, answers, risk_level="high", score=8, reasons=["Severe pain", "Fever"])

    generator = DeterministicCareSummaryGenerator()
    data = generator.generate(call)

    assert data.patient_name == "Demo Patient Z"
    assert "Fever reported" in data.symptoms_reported
    assert any("Pain level 9" in s for s in data.symptoms_reported)
    assert data.risk_score == 8
    assert "Immediate nurse review" in data.recommended_next_step


def test_low_risk_summary_reports_no_concerning_symptoms(app, db):
    answers = {
        "pain_level": 1,
        "fever": False,
        "medication_collected": True,
        "medication_taken": True,
        "bleeding": False,
        "swelling": False,
        "difficulty_breathing": False,
        "general_recovery": "improving",
    }
    call = _make_completed_call(db, answers, risk_level="low", score=0, reasons=["No concerning factors"])

    generator = DeterministicCareSummaryGenerator()
    data = generator.generate(call)

    assert data.symptoms_reported == ["No concerning symptoms reported"]
    assert "No immediate action" in data.recommended_next_step


def test_generate_and_store_summary_persists_row(app, db):
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
    call = _make_completed_call(db, answers, risk_level="low", score=0, reasons=["No concerning factors"])

    summary = generate_and_store_summary(call)
    db.session.commit()

    assert summary.id is not None
    assert summary.call_id == call.id
    assert call.care_summary is not None
    assert call.care_summary.generated_by == "deterministic_v1"


def test_current_string_contract_high_risk_summary_reports_concerning_symptoms(app, db):
    """Regression: CALL-E's string contract must remain visible in Care Summary."""
    answers = {
        "pain_level": "9",
        "fever": "yes",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "yes",
        "general_recovery": "getting worse",
    }
    call = _make_completed_call(
        db,
        answers,
        risk_level="high",
        score=16,
        reasons=[
            "Pain level 9/10 is severe",
            "Patient reports fever",
            "Patient reports difficulty breathing",
        ],
    )

    data = DeterministicCareSummaryGenerator().generate(call)

    assert "Fever reported" in data.symptoms_reported
    assert "Difficulty breathing reported" in data.symptoms_reported
    assert "Pain level 9/10" in data.symptoms_reported
    assert "No concerning symptoms reported" not in data.symptoms_reported


def test_current_string_contract_reassuring_answers_remain_reassuring(app, db):
    """Current CALL-E string values should preserve the normal low-risk summary."""
    answers = {
        "pain_level": "2",
        "fever": "no",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "no",
        "general_recovery": "improving",
    }
    call = _make_completed_call(db, answers, risk_level="low", score=0)

    data = DeterministicCareSummaryGenerator().generate(call)

    assert data.symptoms_reported == ["No concerning symptoms reported"]


def test_unknown_symptom_answer_is_not_summarized_as_reassuring(app, db):
    """Unknown/unavailable answers must never silently become 'no concern'."""
    answers = {
        "pain_level": "unknown",
        "fever": "unknown",
        "medication_collected": "yes",
        "medication_taken": "yes",
        "bleeding": "no",
        "swelling": "no",
        "difficulty_breathing": "no",
        "general_recovery": "improving",
    }
    call = _make_completed_call(db, answers, risk_level="medium", score=4)

    data = DeterministicCareSummaryGenerator().generate(call)

    assert "No concerning symptoms reported" not in data.symptoms_reported
    assert "Some symptom responses were unavailable" in data.symptoms_reported
