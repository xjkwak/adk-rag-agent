"""Provider availability helpers for multi-model support."""

from __future__ import annotations

import json
import os

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"

_ALL_PROVIDERS: list[dict[str, str]] = [
    {"id": PROVIDER_GEMINI, "label": "Gemini"},
    {"id": PROVIDER_OPENAI, "label": "OpenAI"},
]


def resolve_openai_key() -> str | None:
    """
    Return the active OpenAI API key.

    Priority: agent_settings.json stored key → OPENAI_API_KEY env var.
    Reads the JSON file directly to avoid circular imports with
    settings_store.load_settings().
    """
    try:
        from .settings_store import SETTINGS_PATH

        if SETTINGS_PATH.exists():
            raw = json.loads(
                SETTINGS_PATH.read_text(encoding="utf-8")
            )
            key = raw.get("openai_api_key", "").strip()
            if key:
                return key
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY", "").strip() or None


def get_available_providers() -> list[dict[str, str]]:
    """
    Return all provider descriptors.

    Both Gemini and OpenAI are always returned so the UI can always
    show both options. Use openai_api_key_set / resolve_openai_key()
    to check whether a key is actually configured.
    """
    return list(_ALL_PROVIDERS)


def is_provider_available(provider: str) -> bool:
    """Return True if the given provider has a usable key/config."""
    if provider == PROVIDER_GEMINI:
        return True
    if provider == PROVIDER_OPENAI:
        return bool(resolve_openai_key())
    return False
