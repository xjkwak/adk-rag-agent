"""OpenAI model catalog for the Configuration UI."""

from __future__ import annotations

# Curated subset of OpenAI models suitable for chat and NLU tasks.
STATIC_OPENAI_MODELS: list[str] = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
]


def get_available_openai_models() -> list[str]:
    """Return the curated OpenAI model list."""
    return list(STATIC_OPENAI_MODELS)
