"""
Demo Mode.

One function call runs the entire CareFlow workflow end to end for a chosen
scenario: create a synthetic patient, discharge them, initiate a CALL-E
follow-up, simulate the webhook, and let the orchestrator run risk
assessment, escalation, and care summary generation exactly as it would for
a real call.

Design decision — always uses the mock voice client, regardless of the
app's configured VOICE_PROVIDER: Demo Mode's entire purpose is a
deterministic, one-click, no-credential-required walkthrough (e.g. for a
judge who hasn't set up CALL-E credentials, or for a reliable live demo
that can't depend on a real phone call completing in front of an audience).
Real CALL-E calls stay available through the normal discharge -> initiate
call -> real webhook path; Demo Mode is a separate, explicitly-labeled lane
that never touches live call credits.
"""
import uuid

from app.extensions import db, logger
from app.models.discharge import Discharge
from app.models.patient import Patient
from app.services import timeline_service
from app.services.call_orchestrator import CallOrchestrator
from app.services.calle.base import CallRequest
from app.services.calle.mock_client import MockVoiceClient
from app.services.demo_scenarios import DEMO_SCENARIOS
from app.services.notifications.log_notifier import LogNotificationService
from app.services.recovery_questions import STANDARD_RECOVERY_QUESTIONS


class UnknownDemoScenarioError(ValueError):
    pass


def run_demo_scenario(scenario_key: str):
    """
    Run one full demo scenario and return the resulting FollowUpCall (with
    its discharge/patient/risk_assessment/care_summary/escalation available
    via relationships for the caller to render).
    """
    scenario = DEMO_SCENARIOS.get(scenario_key)
    if scenario is None:
        raise UnknownDemoScenarioError(
            f"Unknown demo scenario '{scenario_key}'. Valid options: {list(DEMO_SCENARIOS)}"
        )

    suffix = uuid.uuid4().hex[:6].upper()
    patient = Patient(
        full_name=f"Demo Patient ({scenario.label} {suffix})",
        synthetic_mrn=f"SYN-DEMO-{suffix}",
        phone_number="+15550000000",
    )
    db.session.add(patient)
    db.session.flush()

    timeline_service.log_event(
        event_type="demo_scenario_started",
        title=f"Demo scenario started: {scenario.label}",
        description=scenario.description,
        patient_id=patient.id,
        metadata={"scenario_key": scenario.key},
        commit=False,
    )
    timeline_service.log_event(
        event_type="patient_created",
        title=f"Patient created: {patient.full_name}",
        description=f"Synthetic MRN {patient.synthetic_mrn}",
        patient_id=patient.id,
        commit=False,
    )

    discharge = Discharge(patient_id=patient.id, diagnosis=scenario.diagnosis)
    db.session.add(discharge)
    db.session.flush()

    timeline_service.log_event(
        event_type="patient_discharged",
        title=f"{patient.full_name} discharged",
        description=f"Diagnosis: {scenario.diagnosis}",
        patient_id=patient.id,
        discharge_id=discharge.id,
        commit=False,
    )
    db.session.commit()

    mock_client = MockVoiceClient()
    notification_service = LogNotificationService()
    orchestrator = CallOrchestrator(mock_client, notification_service)

    call = orchestrator.initiate_follow_up_call(discharge)

    call_request = CallRequest(
        patient_name=patient.full_name,
        phone_number=patient.phone_number,
        discharge_diagnosis=discharge.diagnosis,
        questions=STANDARD_RECOVERY_QUESTIONS,
        reference_id=str(call.id),
    )
    payload = mock_client.simulate_completed_call(
        call.provider_call_id, call_request, scenario=scenario.mock_scenario
    )
    call = orchestrator.process_webhook_event(payload)

    logger.info("Demo scenario '%s' completed for call %s", scenario_key, call.id)
    return call
