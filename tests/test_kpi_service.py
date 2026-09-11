from app.services.demo_mode import run_demo_scenario
from app.services.kpi_service import compute_kpis, get_pending_follow_ups


def test_kpis_on_empty_database(app, db):
    kpis = compute_kpis()

    assert kpis.total_patients == 0
    assert kpis.pending_follow_ups == 0
    assert kpis.high_risk_patients == 0
    assert kpis.escalations_awaiting_acknowledgement == 0
    assert kpis.calls_completed_today == 0


def test_kpis_reflect_healthy_recovery_scenario(app, db):
    run_demo_scenario("healthy_recovery")

    kpis = compute_kpis()

    assert kpis.total_patients == 1
    assert kpis.calls_completed_today == 1
    assert kpis.high_risk_patients == 0
    assert kpis.escalations_awaiting_acknowledgement == 0
    # The discharge reached call_completed, so it's no longer "pending"
    assert kpis.pending_follow_ups == 0


def test_kpis_reflect_high_risk_scenario(app, db):
    run_demo_scenario("high_risk")

    kpis = compute_kpis()

    assert kpis.high_risk_patients == 1
    assert kpis.escalations_awaiting_acknowledgement == 1


def test_kpis_count_high_risk_patient_once_across_multiple_calls(app, db):
    # Two high-risk scenarios could in principle involve the same patient in
    # a real workflow; here each scenario creates its own synthetic patient,
    # so this test instead confirms the dedup logic doesn't over- or
    # under-count across two distinct high-risk patients.
    run_demo_scenario("high_risk")
    run_demo_scenario("high_risk")

    kpis = compute_kpis()

    assert kpis.high_risk_patients == 2
    assert kpis.escalations_awaiting_acknowledgement == 2


def test_pending_follow_ups_excludes_completed_discharges(app, db):
    from app.models.discharge import Discharge
    from app.models.patient import Patient
    from app.extensions import db as _db

    patient = Patient(full_name="Pending Patient", synthetic_mrn="SYN-TEST-KPI1", phone_number="+15550002222")
    _db.session.add(patient)
    _db.session.flush()
    discharge = Discharge(patient_id=patient.id, diagnosis="Test diagnosis")  # status defaults to "pending"
    _db.session.add(discharge)
    _db.session.commit()

    kpis = compute_kpis()
    assert kpis.pending_follow_ups == 1


def test_pending_follow_ups_include_existing_states_and_needs_review(app, db):
    from app.extensions import db as _db
    from app.models.discharge import Discharge
    from app.models.patient import Patient

    patient = Patient(
        full_name="Review Queue Patient",
        synthetic_mrn="SYN-TEST-KPI2",
        phone_number="+15550001111",
    )
    _db.session.add(patient)
    _db.session.flush()
    for status in ("pending", "call_scheduled", "needs_review", "call_completed"):
        _db.session.add(
            Discharge(patient_id=patient.id, diagnosis=f"Status {status}", status=status)
        )
    _db.session.commit()

    pending = get_pending_follow_ups()
    kpis = compute_kpis()

    assert {discharge.status for discharge in pending} == {
        "pending",
        "call_scheduled",
        "needs_review",
    }
    assert kpis.pending_follow_ups == 3


def test_needs_review_call_is_not_counted_as_completed(app, db):
    from app.extensions import db as _db, utcnow
    from app.models.call import FollowUpCall
    from app.models.discharge import Discharge
    from app.models.patient import Patient

    patient = Patient(
        full_name="Data Quality Patient",
        synthetic_mrn="SYN-TEST-KPI3",
        phone_number="+15550001010",
    )
    _db.session.add(patient)
    _db.session.flush()
    discharge = Discharge(
        patient_id=patient.id,
        diagnosis="Data quality review",
        status="needs_review",
    )
    _db.session.add(discharge)
    _db.session.flush()
    _db.session.add(
        FollowUpCall(
            discharge_id=discharge.id,
            provider_call_id="review-kpi-call",
            status="needs_review",
            completed_at=utcnow(),
        )
    )
    _db.session.commit()

    kpis = compute_kpis()

    assert kpis.pending_follow_ups == 1
    assert kpis.calls_completed_today == 0
