"""Shared scenario definitions for Demo Mode and its dashboard picker.

Each synthetic diagnosis maps to a deterministic mock-provider outcome.
"""
from dataclasses import dataclass


@dataclass
class DemoScenario:
    key: str
    label: str
    description: str
    diagnosis: str
    mock_scenario: str
    expected_outcome: str


DEMO_SCENARIOS = {
    "healthy_recovery": DemoScenario(
        key="healthy_recovery",
        label="Healthy Recovery",
        description="Patient reports no concerning symptoms. No escalation.",
        diagnosis="Appendectomy recovery",
        mock_scenario="healthy_recovery",
        expected_outcome="risk_level=low, no escalation, care summary generated",
    ),
    "moderate_concern": DemoScenario(
        key="moderate_concern",
        label="Moderate Concern",
        description="Patient reports moderate pain and a fever. Flagged for routine follow-up, not escalated.",
        diagnosis="Hip replacement recovery",
        mock_scenario="moderate_concern",
        expected_outcome="risk_level=medium, no escalation, care summary generated",
    ),
    "high_risk": DemoScenario(
        key="high_risk",
        label="High Risk",
        description="Patient reports severe pain, fever, and difficulty breathing. Triggers immediate escalation.",
        diagnosis="Pneumonia treatment",
        mock_scenario="high_risk",
        expected_outcome="risk_level=high, escalation triggered and notified, care summary generated",
    ),
    "failed_call": DemoScenario(
        key="failed_call",
        label="Failed Call",
        description="CALL-E reports the call could not be connected. No risk assessment is possible.",
        diagnosis="Cardiac catheterization recovery",
        mock_scenario="failed_call",
        expected_outcome="call status=failed, no risk assessment, no care summary",
    ),
    "no_answer": DemoScenario(
        key="no_answer",
        label="No Answer",
        description="The patient never picks up. No risk assessment is possible.",
        diagnosis="Gallbladder removal recovery",
        mock_scenario="no_answer",
        expected_outcome="call status=no_answer, no risk assessment, no care summary",
    ),
}
