"""Gemini NLU helpers for classification, extraction, and summarization."""

from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types

from ..adapters.knowledge_hub import get_intake_search_corpus, normalize_coderoad_collected_fields
from ..config_loader import get_request_types
from ..genai_utils import generate_content
from .field_heuristics import (
    build_ticket_description_heuristic,
    build_ticket_title_heuristic,
    classify_request_heuristic,
    extract_coderoad_fields_heuristic,
)
from .intake_fields import extract_explicit_fields

logger = logging.getLogger(__name__)


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
    heuristic = classify_request_heuristic(messages)
    if heuristic:
        logger.info("Classified request via heuristics as %s", heuristic)
        return heuristic

    types_cfg = get_request_types()
    allowed = list(types_cfg.keys())
    labels = {k: v.get("label", k) for k, v in types_cfg.items()}
    prompt = f"""Classify the support request into exactly one category for three-flow intake.

**Flow 1 — New feature request** → feature_request
User wants new functionality, enhancement, or capability (Jira Story).

**Flow 2 — Known bug** → known_issue or faq
Bug or problem that may match a documented KB fix; try self-service first.

**Flow 3 — Unknown bug** → technical_incident, unclear, or unsupported
New/defect incident with no known KB article; opens a Jira Bug with full context.

Allowed category keys (return one exactly):
{json.dumps(labels, indent=2)}

Conversation:
{_messages_text(messages)}

Respond with JSON only: {{"request_type": "<key>"}}
"""
    response_text = generate_content(
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    result = _parse_json_response(response_text or "{}")
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

    merged = dict(existing)
    heuristic = extract_explicit_fields(messages, field_names, merged)
    for key, value in heuristic.items():
        if value is not None:
            merged[key] = value

    if get_intake_search_corpus() == "amtech-demo":
        coderoad = extract_coderoad_fields_heuristic(messages, merged, field_names)
        for key, value in coderoad.items():
            if value is not None:
                merged[key] = value

    missing_for_llm = [
        name
        for name in field_names
        if merged.get(name) is None or merged.get(name) == ""
    ]
    if not missing_for_llm:
        if get_intake_search_corpus() == "amtech-demo":
            normalize_coderoad_collected_fields(merged, _messages_text(messages))
        return {
            name: merged[name]
            for name in field_names
            if name in merged and merged[name] not in (None, "")
        }

    if get_intake_search_corpus() == "amtech-demo":
        coderoad_core = {"module", "identifier", "description", "environment"}
        if merged.get("module") and merged.get("description"):
            if set(missing_for_llm) <= coderoad_core:
                logger.info(
                    "Skipping LLM field extraction; missing %s will be collected via prompts",
                    missing_for_llm,
                )
                normalize_coderoad_collected_fields(
                    merged, _messages_text(messages)
                )
                return {
                    name: merged[name]
                    for name in field_names
                    if name in merged and merged[name] not in (None, "")
                }

    prompt = f"""Extract structured support intake fields from the conversation.
Request type: {request_type}
Fields to extract: {missing_for_llm}
Already collected (do not overwrite unless user corrected): {json.dumps(merged)}

Rules:
- Only extract values explicitly stated or clearly implied.
- Use null for unknown fields.
- Do not invent information.

Conversation:
{_messages_text(messages)}

Respond with JSON only: a flat object with field names as keys.
"""
    response_text = generate_content(
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    result = _parse_json_response(response_text or "{}")
    for name in missing_for_llm:
        val = result.get(name)
        if val is not None and val != "" and val != "null":
            merged[name] = val

    if get_intake_search_corpus() == "amtech-demo":
        full_text = _messages_text(messages)
        normalize_coderoad_collected_fields(merged, full_text)

    extracted: dict[str, Any] = {}
    for name in field_names:
        val = merged.get(name)
        if val is not None and val != "" and val != "null":
            extracted[name] = val
    return extracted


def generate_conversation_summary(
    collected_fields: dict[str, Any],
    request_type: str,
    messages: list[dict[str, str]],
    kb_results: list[dict[str, Any]] | None = None,
) -> str:
    heuristic = build_ticket_description_heuristic(
        collected_fields, request_type, messages
    )
    if collected_fields.get("module") or collected_fields.get("description"):
        return heuristic

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
    return generate_content(
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )


def generate_ticket_summary(collected_fields: dict[str, Any], request_type: str) -> str:
    heuristic = build_ticket_title_heuristic(collected_fields, request_type)
    if collected_fields.get("module") or collected_fields.get("description"):
        return heuristic

    prompt = f"""Create a concise Jira issue summary (max 80 chars) for this support request.
Request type: {request_type}
Fields: {json.dumps(collected_fields)}

Return plain text only, no quotes.
"""
    text = generate_content(
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return (text or heuristic).strip().strip('"')[:80]


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
