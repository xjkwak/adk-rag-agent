"""Gemini speech-to-text adapter."""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from ..config import (
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_GENAI_USE_VERTEXAI,
    STT_MODEL,
)

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/flac",
    "audio/aac",
    "audio/aiff",
}

MAX_INLINE_BYTES = 20 * 1024 * 1024


def _get_client() -> genai.Client:
    if GOOGLE_GENAI_USE_VERTEXAI:
        return genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
        )
    return genai.Client()


def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported audio format: {mime_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )
    if len(audio_bytes) > MAX_INLINE_BYTES:
        raise ValueError(
            f"Audio file too large ({len(audio_bytes)} bytes). Maximum is {MAX_INLINE_BYTES}."
        )

    client = _get_client()
    prompt = (
        "Transcribe this support request audio verbatim. "
        "Return only the spoken text, no commentary."
    )

    response = client.models.generate_content(
        model=STT_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(temperature=0.0),
    )
    transcript = (response.text or "").strip()
    if not transcript:
        raise ValueError("Could not transcribe audio. Please try again or type your message.")
    logger.info("Transcribed %d bytes -> %d chars", len(audio_bytes), len(transcript))
    return transcript
