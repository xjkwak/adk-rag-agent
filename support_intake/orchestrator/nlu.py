"""Gemini NLU helpers for classification, extraction, and summarization."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ..config import (
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_GENAI_USE_VERTEXAI,
    NLU_MODEL,
)
from ..config_loader import get_request_types

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
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


def _messages_text(messages: list[dict[str, str]]) -> str:
    lines = []
    for m in messages:
        role = m.get("role", "user").upper()
        lines.append(f"{role}: {m.get('content', '')}")
    return "\n".join(lines)


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def classify_request(messages: list[dict[str, str]]) -> str:
    types_cfg = get_request_types()
    allowed = list(types_cfg.keys())
    labels = {k: v.get("label", k) for k, v in types_cfg.items()}
    prompt = f"""Classify the support request into exactly one category.

Allowed categories (return the key exactly):
{json.dumps(labels, indent=2)}

Conversation:
{_messages_text(messages)}

Respond with JSON only: {{"request_type": "<key>"}}
"""
    client = _get_client()
    response = client.models.generate_content(
        model=NLU_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    result = _parse_json_response(response.text or "{}")
    request_type = result.get("request_type", "unclear")
    if request_type not in allowed:
        return "unclear"
    return request_type


def extract_fields(
    messages: list[dict[str, str]],
    request_type: str,
    field_names: list[str],
    existing: dict[str, Any],
) -> dict[str, Any]:
    if not field_names:
        return {}

    prompt = f"""Extract structured support intake fields from the conversation.
Request type: {request_type}
Fields to extract: {field_names}
Already collected (do not overwrite unless user corrected): {json.dumps(existing)}

Rules:
- Only extract values explicitly stated or clearly implied.
- Use null for unknown fields.
- Do not invent information.

Conversation:
{_messages_text(messages)}

Respond with JSON only: a flat object with field names as keys.
"""
    client = _get_client()
    response = client.models.generate_content(
        model=NLU_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    result = _parse_json_response(response.text or "{}")
    extracted: dict[str, Any] = {}
    for name in field_names:
        val = result.get(name)
        if val is not None and val != "" and val != "null":
            extracted[name] = val
    return extracted


def generate_conversation_summary(
    collected_fields: dict[str, Any],
    request_type: str,
    messages: list[dict[str, str]],
    kb_results: list[dict[str, Any]] | None = None,
) -> str:
    kb_section = ""
    if kb_results:
        kb_section = f"\nKnowledge Hub results consulted:\n{json.dumps(kb_results[:3], indent=2)}"

    prompt = f"""Write a concise Markdown summary for a Jira ticket description.
Include: problem description, environment, impact, steps to reproduce if known.
Do NOT include the full raw chat transcript.
Use bullet points where helpful.

Request type: {request_type}
Collected fields: {json.dumps(collected_fields, indent=2)}
{kb_section}

Recent conversation:
{_messages_text(messages[-6:])}

Return Markdown text only (no JSON wrapper).
"""
    client = _get_client()
    response = client.models.generate_content(
        model=NLU_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return (response.text or "").strip()


def generate_ticket_summary(collected_fields: dict[str, Any], request_type: str) -> str:
    """Generate a short ticket title."""
    prompt = f"""Create a concise Jira issue summary (max 80 chars) for this support request.
Request type: {request_type}
Fields: {json.dumps(collected_fields)}

Return plain text only, no quotes.
"""
    client = _get_client()
    response = client.models.generate_content(
        model=NLU_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    text = (response.text or "Support request").strip().strip('"')
    return text[:80]


def detect_solution_feedback(user_message: str) -> bool | None:
    """Return True if resolved, False if not, None if unclear."""
    lower = user_message.lower().strip()
    positive = (
        "yes",
        "worked",
        "fixed",
        "resolved",
        "thanks",
        "thank you",
        "that helped",
        "solved",
    )
    negative = (
        "no",
        "didn't work",
        "did not work",
        "not work",
        "still broken",
        "still have",
        "doesn't help",
        "create a ticket",
        "create ticket",
        "open a ticket",
    )
    if any(p in lower for p in positive) and not any(n in lower for n in negative):
        return True
    if any(n in lower for n in negative):
        return False
    return None


def detect_ticket_confirmation(user_message: str) -> bool | None:
    lower = user_message.lower().strip()
    if lower in ("yes", "confirm", "confirmed", "create", "submit", "ok", "okay"):
        return True
    if lower in ("no", "cancel", "edit", "change", "modify"):
        return False
    return None
