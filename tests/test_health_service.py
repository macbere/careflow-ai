from app.services.demo_mode import run_demo_scenario
from app.services.health_service import compute_health


def test_health_reports_mock_provider_as_ready(app, db):
    health = compute_health({"VOICE_PROVIDER": "mock", "NOTIFICATION_PROVIDER": "log"})

    assert health.voice_provider == "mock"
    assert health.voice_provider_status == "ready"
    assert health.notification_service == "log"
    assert health.database_status == "connected"
    assert health.demo_mode_available is True
    assert health.demo_scenario_count == 5


def test_health_reports_calle_not_configured_without_api_key(app, db):
    health = compute_health({"VOICE_PROVIDER": "calle", "CALLE_API_KEY": ""})

    assert health.voice_provider == "calle"
    assert "not configured" in health.voice_provider_status


def test_health_reports_calle_ready_with_api_key(app, db):
    health = compute_health({"VOICE_PROVIDER": "calle", "CALLE_API_KEY": "sk-test-123"})

    assert health.voice_provider_status == "ready"


def test_health_last_webhook_reflects_recent_call_completion(app, db):
    health_before = compute_health({"VOICE_PROVIDER": "mock"})
    assert health_before.last_webhook_at is None

    run_demo_scenario("healthy_recovery")

    health_after = compute_health({"VOICE_PROVIDER": "mock"})
    assert health_after.last_webhook_at is not None
