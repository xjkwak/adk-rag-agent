"""Rule-based field extraction and classification to reduce Gemini calls."""

from __future__ import annotations

import re
from typing import Any

from ..adapters.knowledge_hub import (
    _infer_identifier_from_text,
    _infer_module_from_text,
    get_intake_search_corpus,
    normalize_coderoad_environment,
)


def _user_messages_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(
        m.get("content", "")
        for m in messages
        if m.get("role") == "user" and m.get("content")
    )


def _latest_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", "")).strip()
    return ""


def classify_request_heuristic(messages: list[dict[str, str]]) -> str | None:
    """Return a request_type key without calling Gemini when patterns are clear."""
    text = _user_messages_text(messages).lower()
    if not text:
        return None

    if any(
        phrase in text
        for phrase in (
            "feature request",
            "new feature",
            "would like to add",
            "enhancement",
        )
    ):
        return "feature_request"
    if any(
        phrase in text
        for phrase in ("access request", "need access", "permission", "permissions")
    ):
        return "access_request"
    if any(
        phrase in text
        for phrase in (
            "known issue",
            "known bug",
            "documented",
            "kb-",
            "already reported",
        )
    ):
        return "known_issue"
    if any(
        phrase in text
        for phrase in (
            "error",
            "warning",
            "broken",
            "failed",
            "not working",
            "duplicate",
            "black screen",
            "blank screen",
            "incident",
            "outage",
            "bug",
        )
    ):
        return "technical_incident"
    if any(phrase in text for phrase in ("how do i", "how to", "what is", "faq")):
        return "faq"
    return None


def extract_coderoad_fields_heuristic(
    messages: list[dict[str, str]],
    existing: dict[str, Any],
    field_names: list[str],
) -> dict[str, Any]:
    """Fill CoderoadERP variables from conversation text without Gemini."""
    if get_intake_search_corpus() != "amtech-demo":
        return {}

    latest = _latest_user_message(messages)
    full_user_text = _user_messages_text(messages)
    merged = dict(existing)
    extracted: dict[str, Any] = {}

    if "environment" in field_names:
        env = normalize_coderoad_environment(
            merged.get("environment"), latest or full_user_text
        )
        if env and merged.get("environment") != env:
            extracted["environment"] = env

    if "module" in field_names and not merged.get("module"):
        module = _infer_module_from_text(full_user_text) or merged.get("system")
        if module:
            extracted["module"] = module

    if "identifier" in field_names and not merged.get("identifier"):
        for key in ("identifier", "document_id", "order_id", "batch_id"):
            if merged.get(key):
                extracted["identifier"] = merged[key]
                break
        if "identifier" not in extracted:
            inferred = _infer_identifier_from_text(full_user_text)
            if inferred:
                extracted["identifier"] = inferred
            elif len(latest.split()) <= 6 and latest and not re.search(
                r"\b(live|test|production|staging)\b", latest.lower()
            ):
                # Short follow-up likely answering the document/record ID prompt.
                extracted["identifier"] = latest.strip()

    if "description" in field_names and not merged.get("description"):
        description = (
            merged.get("actual_behavior")
            or merged.get("summary")
            or (full_user_text if len(full_user_text) > 12 else None)
        )
        if description:
            extracted["description"] = description

    for key in ("system", "actual_behavior", "summary", "error_message"):
        if key in field_names and not merged.get(key) and latest:
            if key == "system" and _infer_module_from_text(latest):
                extracted["system"] = _infer_module_from_text(latest)
            elif key in ("actual_behavior", "summary") and len(latest) > 20:
                extracted[key] = latest

    return extracted


def build_ticket_title_heuristic(
    collected_fields: dict[str, Any],
    request_type: str,
) -> str:
    module = str(
        collected_fields.get("module")
        or collected_fields.get("system")
        or "CoderoadERP"
    ).strip()
    identifier = str(collected_fields.get("identifier", "")).strip()
    description = str(
        collected_fields.get("description")
        or collected_fields.get("actual_behavior")
        or collected_fields.get("summary")
        or request_type.replace("_", " ")
    ).strip()
    first_sentence = re.split(r"[.!?\n]", description, maxsplit=1)[0].strip()
    parts = [module]
    if identifier:
        parts.append(identifier)
    if first_sentence:
        parts.append(first_sentence[:50])
    title = " — ".join(parts)
    return title[:80] if title else "Support request"


def build_ticket_description_heuristic(
    collected_fields: dict[str, Any],
    request_type: str,
    messages: list[dict[str, str]],
) -> str:
    lines = [
        f"**Request type:** {request_type.replace('_', ' ').title()}",
        "",
        "**Collected details**",
    ]
    label_map = {
        "module": "Module",
        "identifier": "Document / Record ID",
        "description": "Description",
        "environment": "Environment",
        "system": "System",
        "actual_behavior": "Actual behavior",
        "error_message": "Error message",
        "business_impact": "Business impact",
    }
    for key, label in label_map.items():
        value = collected_fields.get(key)
        if value:
            lines.append(f"- **{label}:** {value}")

    user_lines = [
        m.get("content", "")
        for m in messages
        if m.get("role") == "user" and m.get("content")
    ]
    if user_lines:
        lines.extend(["", "**User messages**"])
        lines.extend(f"- {text}" for text in user_lines[-4:])

    return "\n".join(lines)
