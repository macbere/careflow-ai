"""
Dashboard — Phase 2 operations console.

Design goal per the Phase 2 brief: the landing page should immediately
answer four questions (which patients need attention, which follow-ups are
pending, which escalations are unresolved, which calls completed today) —
so those four queries are what this module is built around, not a generic
"list everything" view.

This module also hosts the demo action routes (create patient, discharge +
initiate call, simulate webhook) as plain HTML form POSTs that redirect
back to the dashboard. Plain forms (no JS) are used deliberately: this is
demo-video-friendly (every state change is a full page load showing the
new state) and keeps the reviewer's demo path fully readable as Flask
routes rather than client-side JS. The underlying logic is identical to the
JSON API in app/api/*.py — these routes are thin wrappers, not a second
implementation.
"""
import uuid
from datetime import timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.extensions import db, utcnow
from app.models.call import FollowUpCall
from app.models.discharge import Discharge
from app.models.escalation import EscalationEvent
from app.models.patient import Patient
from app.models.risk_assessment import RiskAssessment
from app.models.timeline_event import TimelineEvent
from app.services import timeline_service
from app.services.call_orchestrator import CallOrchestrator
from app.services.calle import get_voice_client
from app.services.calle.base import CallRequest
from app.services.calle.mock_client import MockVoiceClient
from app.services.demo_mode import UnknownDemoScenarioError, run_demo_scenario
from app.services.demo_scenarios import DEMO_SCENARIOS
from app.services.escalation_service import acknowledge_escalation
from app.services.health_service import compute_health
from app.services.kpi_service import compute_kpis, get_pending_follow_ups
from app.services.notifications import get_notification_service
from app.services.recovery_questions import STANDARD_RECOVERY_QUESTIONS
from app.services.timeline_service import get_timeline

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


# ---------------------------------------------------------------------------
# Read views
# ---------------------------------------------------------------------------


@dashboard_bp.get("")
def index():
    # 1. Which patients need attention? -> unresolved (non-acknowledged)
    #    escalations, newest first.
    needs_attention = (
        EscalationEvent.query.join(RiskAssessment)
        .filter(EscalationEvent.status != "acknowledged")
        .order_by(EscalationEvent.triggered_at.desc())
        .all()
    )

    # 2. Which follow-ups are pending? -> discharges that haven't had a
    #    completed valid result yet, including data-quality holds that
    #    explicitly require human review.
    pending_follow_ups = get_pending_follow_ups()

    # 3. Which escalations remain unresolved? (same underlying set as #1,
    #    shown as its own panel since the brief calls it out separately —
    #    "needs attention" foregrounds the patient, this panel foregrounds
    #    the escalation workflow state.)
    unresolved_escalations = needs_attention

    # 4. Which calls were completed today?
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    calls_completed_today = (
        FollowUpCall.query.filter(
            FollowUpCall.status == "completed", FollowUpCall.completed_at >= today_start
        )
        .order_by(FollowUpCall.completed_at.desc())
        .all()
    )

    patients = Patient.query.order_by(Patient.created_at.desc()).all()
    recent_events = get_timeline(limit=30)[::-1]  # newest first for the feed
    kpis = compute_kpis()
    health = compute_health(current_app.config)

    return render_template(
        "dashboard.html",
        needs_attention=needs_attention,
        pending_follow_ups=pending_follow_ups,
        unresolved_escalations=unresolved_escalations,
        calls_completed_today=calls_completed_today,
        patients=patients,
        recent_events=recent_events,
        kpis=kpis,
        health=health,
        demo_scenarios=DEMO_SCENARIOS,
        voice_provider=current_app.config.get("VOICE_PROVIDER", "mock"),
    )


@dashboard_bp.get("/calls/<int:call_id>")
def call_detail(call_id):
    call = FollowUpCall.query.get_or_404(call_id)
    timeline = TimelineEvent.query.filter_by(call_id=call_id).order_by(TimelineEvent.created_at.asc()).all()

    return render_template(
        "call_detail.html",
        call=call,
        timeline=timeline,
        voice_provider=current_app.config.get("VOICE_PROVIDER", "mock"),
    )


# ---------------------------------------------------------------------------
# Demo action routes (form POSTs, redirect back to a page)
# ---------------------------------------------------------------------------


@dashboard_bp.post("/patients")
def create_patient_form():
    full_name = request.form.get("full_name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()

    if not full_name or not phone_number:
        flash("Patient name and phone number are both required.", "error")
        return redirect(url_for("dashboard.index"))

    patient = Patient(
        full_name=full_name,
        synthetic_mrn=f"SYN-{uuid.uuid4().hex[:8].upper()}",
        phone_number=phone_number,
    )
    db.session.add(patient)
    db.session.flush()

    timeline_service.log_event(
        event_type="patient_created",
        title=f"Patient created: {patient.full_name}",
        description=f"Synthetic MRN {patient.synthetic_mrn}",
        patient_id=patient.id,
        commit=False,
    )
    db.session.commit()

    flash(f"Created synthetic patient {patient.full_name} ({patient.synthetic_mrn}).", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.post("/discharges")
def create_discharge_and_call_form():
    """
    Combines "trigger discharge" + "initiate CALL-E follow-up" into one
    submit, matching demo-flow steps 2-3 in a single reviewer action. This
    duplicates no logic — it calls the same Discharge model and
    CallOrchestrator the JSON API uses.
    """
    patient_id = request.form.get("patient_id", type=int)
    diagnosis = request.form.get("diagnosis", "").strip()

    if not patient_id or not diagnosis:
        flash("Select a patient and enter a diagnosis before discharging.", "error")
        return redirect(url_for("dashboard.index"))

    patient = Patient.query.get(patient_id)
    if not patient:
        flash("That patient no longer exists.", "error")
        return redirect(url_for("dashboard.index"))

    discharge = Discharge(patient_id=patient.id, diagnosis=diagnosis)
    db.session.add(discharge)
    db.session.flush()

    timeline_service.log_event(
        event_type="patient_discharged",
        title=f"{patient.full_name} discharged",
        description=f"Diagnosis: {diagnosis}",
        patient_id=patient.id,
        discharge_id=discharge.id,
        commit=False,
    )
    db.session.commit()

    voice_client = get_voice_client(current_app.config)
    notification_service = get_notification_service(current_app.config)
    orchestrator = CallOrchestrator(voice_client, notification_service)
    call = orchestrator.initiate_follow_up_call(discharge)

    if call.status == "failed":
        flash(
            f"{patient.full_name} was discharged, but the follow-up call failed to initiate: {call.failure_reason}",
            "error",
        )
    else:
        flash(f"{patient.full_name} discharged and follow-up call initiated.", "success")

    return redirect(url_for("dashboard.index"))


@dashboard_bp.post("/calls/<int:call_id>/simulate")
def simulate_completion_form(call_id):
    """Mock-mode only: fires the simulated webhook for a given scenario and redirects to the call detail page."""
    if current_app.config.get("VOICE_PROVIDER") != "mock":
        flash("Webhook simulation is only available when VOICE_PROVIDER=mock.", "error")
        return redirect(url_for("dashboard.call_detail", call_id=call_id))

    call = FollowUpCall.query.get_or_404(call_id)
    scenario = request.form.get("scenario", "random")

    if not call.provider_call_id:
        flash("This call has no provider call ID yet — it may have failed to initiate.", "error")
        return redirect(url_for("dashboard.call_detail", call_id=call_id))

    mock_client = MockVoiceClient()
    call_request = CallRequest(
        patient_name=call.discharge.patient.full_name,
        phone_number=call.discharge.patient.phone_number,
        discharge_diagnosis=call.discharge.diagnosis,
        questions=STANDARD_RECOVERY_QUESTIONS,
        reference_id=str(call.id),
    )
    payload = mock_client.simulate_completed_call(call.provider_call_id, call_request, scenario=scenario)

    notification_service = get_notification_service(current_app.config)
    orchestrator = CallOrchestrator(mock_client, notification_service)
    updated_call = orchestrator.process_webhook_event(payload)

    if updated_call.status == "completed":
        flash(f"Webhook simulated ({scenario}) — risk assessment and care summary generated.", "success")
    else:
        flash(f"Webhook simulated: call ended as '{updated_call.status}'.", "info")

    return redirect(url_for("dashboard.call_detail", call_id=call_id))


@dashboard_bp.post("/escalations/<int:escalation_id>/acknowledge")
def acknowledge_escalation_form(escalation_id):
    """Completes the escalation lifecycle: triggered -> notified -> acknowledged."""
    escalation = EscalationEvent.query.get_or_404(escalation_id)
    note = request.form.get("note", "").strip() or None
    acknowledge_escalation(escalation, acknowledged_by="on_call_nurse", note=note)

    flash("Escalation acknowledged.", "success")

    # Redirect back to the call this escalation belongs to, if we can
    # resolve it, otherwise back to the dashboard.
    if escalation.risk_assessment and escalation.risk_assessment.call_id:
        return redirect(url_for("dashboard.call_detail", call_id=escalation.risk_assessment.call_id))
    return redirect(url_for("dashboard.index"))


# ---------------------------------------------------------------------------
# Demo Mode
# ---------------------------------------------------------------------------


@dashboard_bp.get("/demo")
def demo_mode_index():
    """Landing page listing the five deterministic demo scenarios as one-click buttons."""
    return render_template("demo_mode.html", scenarios=DEMO_SCENARIOS)


@dashboard_bp.post("/demo/run")
def demo_mode_run():
    """
    One click runs the entire workflow for a chosen scenario end to end
    (patient -> discharge -> call -> webhook -> risk -> escalation ->
    care summary) and lands the reviewer directly on the resulting call's
    detail page, fully populated.
    """
    scenario_key = request.form.get("scenario_key", "")
    try:
        call = run_demo_scenario(scenario_key)
    except UnknownDemoScenarioError:
        flash(f"Unknown demo scenario '{scenario_key}'.", "error")
        return redirect(url_for("dashboard.demo_mode_index"))

    flash(f"Demo scenario complete: {call.discharge.patient.full_name}.", "success")
    return redirect(url_for("dashboard.call_detail", call_id=call.id))
