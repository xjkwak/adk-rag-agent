"""Vertex AI Gemini model catalog for the Configuration UI."""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

# Curated Gemini models commonly available on Vertex AI (us-central1 and global).
STATIC_VERTEX_GEMINI_MODELS: list[str] = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
    "gemini-1.5-pro",
    "gemini-1.5-pro-002",
    "gemini-1.5-flash",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash-8b-001",
]

_MODEL_SORT_ORDER = {name: index for index, name in enumerate(STATIC_VERTEX_GEMINI_MODELS)}


def _short_model_name(resource_name: str) -> str:
    """Normalize publishers/google/models/gemini-2.5-flash -> gemini-2.5-flash."""
    name = resource_name.strip()
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    return name


def _is_gemini_generate_model(name: str) -> bool:
    lower = name.lower()
    if "gemini" not in lower:
        return False
    if any(token in lower for token in ("embedding", "embed", "aqa", "vision-only")):
        return False
    return bool(re.match(r"^gemini[\w.-]+$", name, re.IGNORECASE))


@lru_cache(maxsize=1)
def _fetch_vertex_gemini_models() -> tuple[str, ...]:
    """Best-effort discovery via Vertex; returns empty tuple when unavailable."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        return ()

    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() in (
        "1",
        "true",
        "yes",
    )
    if not use_vertex:
        return ()

    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1").strip()
    try:
        from google import genai

        client = genai.Client(vertexai=True, project=project, location=location)
        discovered: list[str] = []
        for model in client.models.list():
            short = _short_model_name(getattr(model, "name", "") or "")
            if short and _is_gemini_generate_model(short):
                discovered.append(short)
        return tuple(sorted(set(discovered)))
    except Exception as exc:
        logger.info("Vertex model discovery unavailable, using static list: %s", exc)
        return ()


def _sort_models(models: list[str]) -> list[str]:
    def key(name: str) -> tuple[int, str]:
        return (_MODEL_SORT_ORDER.get(name, 999), name)

    return sorted(set(models), key=key)


def get_available_gemini_models(*, include: str | None = None) -> list[str]:
    """Merged static + discovered Vertex Gemini models for the config dropdown."""
    models = list(STATIC_VERTEX_GEMINI_MODELS)
    models.extend(_fetch_vertex_gemini_models())
    if include:
        models.append(include.strip())
    return _sort_models(models)
