from app.models.call import FollowUpCall
from app.models.discharge import Discharge
from app.models.patient import Patient
from app.models.risk_assessment import RiskAssessment
from app.services.escalation_service import trigger_escalation
from app.services.notifications.base import NotificationRequest, NotificationResult, NotificationService
from app.services.notifications.log_notifier import LogNotificationService
from app.services.notifications import get_notification_service


class FakeNotificationService(NotificationService):
    """Test double proving escalation_service depends only on the abstraction."""

    def __init__(self):
        self.sent = []

    def send(self, request: NotificationRequest) -> NotificationResult:
        self.sent.append(request)
        return NotificationResult(success=True, channel="fake", detail="captured by test double")


def _make_high_risk_assessment(db):
    patient = Patient(full_name="Demo Patient V", synthetic_mrn="SYN-TEST-6", phone_number="+15550004444")
    db.session.add(patient)
    db.session.flush()
    discharge = Discharge(patient_id=patient.id, diagnosis="Test diagnosis")
    db.session.add(discharge)
    db.session.flush()
    call = FollowUpCall(discharge_id=discharge.id, provider_call_id="mock-notif-1", status="completed")
    db.session.add(call)
    db.session.flush()
    assessment = RiskAssessment(call_id=call.id, risk_level="high", score=10, reasons=["Difficulty breathing"])
    db.session.add(assessment)
    db.session.flush()
    return assessment


def test_trigger_escalation_uses_injected_notification_service(app, db):
    assessment = _make_high_risk_assessment(db)
    fake_service = FakeNotificationService()

    event = trigger_escalation(assessment, notification_service=fake_service)

    assert len(fake_service.sent) == 1
    assert "Demo Patient V" in fake_service.sent[0].message
    assert event.status == "notified"
    assert event.action_taken == "captured by test double"


def test_trigger_escalation_defaults_to_log_notification_service(app, db):
    assessment = _make_high_risk_assessment(db)

    event = trigger_escalation(assessment)  # no notification_service passed

    assert event.status == "notified"


def test_get_notification_service_defaults_to_log():
    service = get_notification_service(None)
    assert isinstance(service, LogNotificationService)
