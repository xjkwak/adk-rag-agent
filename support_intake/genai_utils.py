"""Shared Vertex/Gemini client helpers with retry and user-friendly errors."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

from google import genai
from google.genai import types

from .config import (
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_GENAI_USE_VERTEXAI,
    NLU_MODEL,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

RATE_LIMIT_USER_MESSAGE = (
    "The AI service is temporarily busy (rate limit reached). "
    "Please wait a minute and try again. "
    "If this keeps happening during demos, try a lighter model such as "
    "**gemini-2.0-flash-lite** on the Configuration page, or request a quota increase "
    "in Google Cloud Console."
)


class IntakeServiceError(Exception):
    """Raised when intake cannot complete an AI step; includes a user-safe message."""

    def __init__(self, user_message: str, *, cause: Exception | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.cause = cause


def get_genai_client() -> genai.Client:
    global _client
    if _client is None:
        if GOOGLE_GENAI_USE_VERTEXAI:
            _client = genai.Client(
                vertexai=True,
                project=GOOGLE_CLOUD_PROJECT,
                location=GOOGLE_CLOUD_LOCATION,
            )
        else:
            _client = genai.Client()
    return _client


def get_intake_model() -> str:
    """Model for Support Intake NLU — prefers Configuration agent model."""
    try:
        from knowledge_hub.settings_store import load_settings

        model = load_settings().get("model", "").strip()
        if model:
            return model
    except Exception:
        logger.debug("Could not load agent model from settings; using NLU_MODEL")
    return NLU_MODEL


def is_rate_limit_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    if "429" in text or "resource_exhausted" in text or "rate limit" in text:
        return True
    status_code = getattr(exc, "status_code", None)
    return status_code == 429


def friendly_error_message(exc: BaseException) -> str:
    if is_rate_limit_error(exc):
        return RATE_LIMIT_USER_MESSAGE
    return (
        "Something went wrong while processing your message. "
        "Please try again in a moment."
    )


def generate_content(
    *,
    contents: str,
    model: str | None = None,
    config: types.GenerateContentConfig | None = None,
    max_retries: int = 3,
    base_delay_s: float = 1.0,
) -> str:
    """Call Gemini with exponential backoff on 429; raises IntakeServiceError when exhausted."""
    client = get_genai_client()
    resolved_model = model or get_intake_model()
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=resolved_model,
                contents=contents,
                config=config,
            )
            return (response.text or "").strip()
        except Exception as exc:
            last_exc = exc
            if is_rate_limit_error(exc) and attempt < max_retries - 1:
                delay = base_delay_s * (2**attempt) + random.uniform(0, 0.25)
                logger.warning(
                    "Vertex rate limit (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            if is_rate_limit_error(exc):
                raise IntakeServiceError(RATE_LIMIT_USER_MESSAGE, cause=exc) from exc
            raise IntakeServiceError(friendly_error_message(exc), cause=exc) from exc

    raise IntakeServiceError(
        friendly_error_message(last_exc or Exception("unknown")),
        cause=last_exc,
    )
