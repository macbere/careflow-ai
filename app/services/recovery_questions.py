"""
Standard structured recovery question set.

This is the single source of truth for what CALL-E asks a patient during a
follow-up call. Keeping it in one place means the risk engine (which expects
specific answer keys) and the call orchestrator (which builds the call
request) can never drift out of sync.
"""
from app.services.calle.base import RecoveryQuestion

STANDARD_RECOVERY_QUESTIONS = [
    RecoveryQuestion(key="pain_level", prompt="On a scale of 0 to 10, how would you rate your pain right now?"),
    RecoveryQuestion(key="fever", prompt="Have you had a fever since you got home?"),
    RecoveryQuestion(key="medication_collected", prompt="Were you able to pick up all of your prescribed medications?"),
    RecoveryQuestion(key="medication_taken", prompt="Have you been taking your medications as prescribed?"),
    RecoveryQuestion(key="bleeding", prompt="Are you experiencing any unexpected bleeding?"),
    RecoveryQuestion(key="swelling", prompt="Have you noticed any unusual swelling?"),
    RecoveryQuestion(key="difficulty_breathing", prompt="Are you having any difficulty breathing?"),
    RecoveryQuestion(key="general_recovery", prompt="Overall, how would you describe how your recovery is going?"),
]
