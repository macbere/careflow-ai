"""
Factory for selecting the active voice provider client based on config.

This is the *only* place that decides mock vs. real CALL-E. Everything else
in the app depends on the abstract VoiceProviderClient interface.
"""
from app.services.calle.base import VoiceProviderClient
from app.services.calle.mock_client import MockVoiceClient


def get_voice_client(config) -> VoiceProviderClient:
    """
    `config` is Flask's `app.config` (or a plain dict in tests) — dict-like,
    not attribute-accessible — so this uses bracket/`.get()` access
    throughout rather than attribute access.
    """
    if config.get("VOICE_PROVIDER") == "calle":
        from app.services.calle.calle_client import CalleVoiceClient

        return CalleVoiceClient(
            api_key=config.get("CALLE_API_KEY", ""),
            base_url=config.get("CALLE_API_BASE_URL", ""),
            webhook_secret=config.get("CALLE_WEBHOOK_SECRET", ""),
            # webhook_url is an optional
            # per-client setting (passed through to each call request) so a
            # deployment can point CALL-E at a specific webhook endpoint
            # (e.g. an ngrok URL) without needing account-level setup.
            webhook_url=config.get("CALLE_WEBHOOK_URL") or None,
        )

    return MockVoiceClient()
