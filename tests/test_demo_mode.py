import pytest

from app.services.demo_mode import UnknownDemoScenarioError, run_demo_scenario


def test_healthy_recovery_scenario_is_low_risk_no_escalation(app, db):
    call = run_demo_scenario("healthy_recovery")

    assert call.status == "completed"
    assert call.risk_assessment.risk_level == "low"
    assert call.risk_assessment.escalation is None
    assert call.care_summary is not None
    assert call.care_summary.escalation_status == "none"


def test_moderate_concern_scenario_is_medium_risk_no_escalation(app, db):
    call = run_demo_scenario("moderate_concern")

    assert call.status == "completed"
    assert call.risk_assessment.risk_level == "medium"
    assert call.risk_assessment.escalation is None
    assert call.care_summary.escalation_status == "none"


def test_high_risk_scenario_triggers_escalation(app, db):
    call = run_demo_scenario("high_risk")

    assert call.status == "completed"
    assert call.risk_assessment.risk_level == "high"
    assert call.risk_assessment.escalation is not None
    assert call.risk_assessment.escalation.status == "notified"
    assert call.care_summary.escalation_status == "notified"


def test_failed_call_scenario_has_no_risk_assessment(app, db):
    call = run_demo_scenario("failed_call")

    assert call.status == "failed"
    assert call.risk_assessment is None
    assert call.care_summary is None


def test_no_answer_scenario_has_no_risk_assessment(app, db):
    call = run_demo_scenario("no_answer")

    assert call.status == "no_answer"
    assert call.risk_assessment is None
    assert call.care_summary is None


def test_unknown_scenario_raises(app, db):
    with pytest.raises(UnknownDemoScenarioError):
        run_demo_scenario("not_a_real_scenario")


def test_demo_scenario_logs_timeline_events(app, db):
    call = run_demo_scenario("healthy_recovery")
    patient_id = call.discharge.patient_id

    from app.services.timeline_service import get_timeline

    event_types = {e.event_type for e in get_timeline(patient_id=patient_id)}
    assert "demo_scenario_started" in event_types
    assert "patient_created" in event_types
    assert "patient_discharged" in event_types
    assert "calle_follow_up_initiated" in event_types
    assert "call_completed" in event_types
    assert "risk_assessment_generated" in event_types
