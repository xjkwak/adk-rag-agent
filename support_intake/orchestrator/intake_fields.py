"""Unified intake field collection — batch prompts and explicit extraction."""

from __future__ import annotations

import re
from typing import Any

from ..adapters.knowledge_hub import (
    get_intake_search_corpus,
    normalize_coderoad_environment,
)
from ..config_loader import (
    format_field_label,
    get_follow_up_question,
    get_global_config,
    get_required_fields,
)
from ..orchestrator.flows import (
    FLOW_FEATURE,
    FLOW_KNOWN_BUG,
    FLOW_UNKNOWN_BUG,
    get_flow_id,
)

# Explicit ID patterns only — never guess from keywords alone.
_IDENTIFIER_PATTERNS = (
    r"\b(INV-\d+)\b",
    r"\b(PO-\d+)\b",
    r"\b(RB-\d+)\b",
    r"\b(CUS-\d+)\b",
    r"\b(GD-\d+)\b",
    r"\b(FG-\d+)\b",
    r"\b(PR-\d+)\b",
    r"\b(SO-\d+)\b",
    r"\b(EMP-\d+)\b",
)

BUG_CORE_FIELDS = ("system", "environment", "identifier", "actual_behavior")

FIELD_PROMPTS: dict[str, str] = {
    "system": "**System / module** — product or workspace affected (e.g. Billing, Logistics).",
    "environment": "**Environment** — LIVE (production) or TEST (staging).",
    "identifier": "**Invoice / record ID** — document, order, or batch number if known.",
    "actual_behavior": "**What is happening** — error message or behavior observed.",
    "module": "**Module** — affected workspace (Billing, Production, Sales, etc.).",
    "description": "**Description** — what you were doing and what went wrong.",
    "business_impact": "**Business impact** — how operations are affected.",
    "summary": "**Summary** — brief description of the issue.",
}

FIELD_OPTIONS: dict[str, list[dict[str, str]]] = {
    "environment": [
        {"value": "LIVE", "label": "LIVE (Production)"},
        {"value": "TEST", "label": "TEST (Staging)"},
    ],
    "module": [
        {"value": "Billing", "label": "Billing"},
        {"value": "Production", "label": "Production"},
        {"value": "Sales", "label": "Sales"},
        {"value": "Logistics", "label": "Logistics"},
        {"value": "Inventory", "label": "Inventory"},
        {"value": "CRM", "label": "CRM"},
        {"value": "IT/Admin", "label": "IT / Admin"},
    ],
}


def _user_messages(messages: list[dict[str, Any]]) -> list[str]:
    return [
        str(m.get("content", "")).strip()
        for m in messages
        if m.get("role") == "user" and str(m.get("content", "")).strip()
    ]


def _latest_user_message(messages: list[dict[str, Any]]) -> str:
    texts = _user_messages(messages)
    return texts[-1] if texts else ""


def _conversation_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(_user_messages(messages))


def get_intake_required_fields(request_type: str) -> list[str]:
    """Required fields for this request, expanded for bug flows."""
    flow_id = get_flow_id(request_type)
    if flow_id in (FLOW_KNOWN_BUG, FLOW_UNKNOWN_BUG):
        required = list(BUG_CORE_FIELDS)
        if get_intake_search_corpus() == "amtech-demo":
            return ["module", "identifier", "description", "environment"]
        return required
    if flow_id == FLOW_FEATURE:
        return get_required_fields(request_type)
    return get_required_fields(request_type)


def _explicit_identifier(text: str) -> str | None:
    for pattern in _IDENTIFIER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    email = re.search(r"([\w.+-]+@[\w.-]+\.\w+)", text)
    if email:
        return email.group(1).lower()
    return None


def _parse_labeled_lines(text: str) -> dict[str, str]:
    """Parse 'System: Billing' or 'Environment: LIVE' from user text."""
    aliases = {
        "system": "system",
        "module": "system",
        "environment": "environment",
        "env": "environment",
        "identifier": "identifier",
        "invoice": "identifier",
        "record id": "identifier",
        "document id": "identifier",
        "document / record id": "identifier",
        "actual behavior": "actual_behavior",
        "description": "actual_behavior",
    }
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        key = aliases.get(label.strip().lower())
        val = value.strip()
        if key and val:
            parsed[key] = val
    return parsed


def extract_explicit_fields(
    messages: list[dict[str, Any]],
    field_names: list[str],
    existing: dict[str, Any],
) -> dict[str, Any]:
    """Extract only values explicitly stated by the user — no keyword guessing."""
    if not field_names:
        return {}

    latest = _latest_user_message(messages)
    full_text = _conversation_text(messages)
    merged = dict(existing)
    extracted: dict[str, Any] = {}

    labeled = _parse_labeled_lines(latest)
    for key, val in labeled.items():
        if key in field_names and val:
            extracted[key] = val

    if "environment" in field_names and "environment" not in extracted:
        env = normalize_coderoad_environment(merged.get("environment"), latest)
        if not env:
            env = normalize_coderoad_environment(None, latest)
        if env:
            extracted["environment"] = env

    if "identifier" in field_names and "identifier" not in extracted:
        for text in (latest, full_text):
            explicit_id = _explicit_identifier(text)
            if explicit_id:
                extracted["identifier"] = explicit_id
                break

    missing_before = [
        name
        for name in field_names
        if not merged.get(name) and name not in extracted
    ]

    # Short single-field follow-up (e.g. user replies "Billing" or "INV-4001").
    if len(missing_before) == 1 and latest and ":" not in latest:
        field = missing_before[0]
        if field == "environment":
            env = normalize_coderoad_environment(None, latest)
            if env:
                extracted["environment"] = env
        elif field == "identifier":
            explicit_id = _explicit_identifier(latest)
            if explicit_id:
                extracted["identifier"] = explicit_id
            elif len(latest.split()) <= 8 and not normalize_coderoad_environment(
                None, latest
            ):
                extracted["identifier"] = latest.strip()
        elif field in ("system", "module") and len(latest.split()) <= 6:
            if not normalize_coderoad_environment(None, latest):
                target = "module" if field == "module" else "system"
                extracted[target] = latest.strip()

    if "actual_behavior" in field_names and "actual_behavior" not in extracted:
        if merged.get("actual_behavior"):
            pass
        elif len(_user_messages(messages)) == 1 and len(latest) > 20:
            extracted["actual_behavior"] = latest

    if "description" in field_names and "description" not in extracted:
        if len(_user_messages(messages)) == 1 and len(latest) > 20:
            extracted["description"] = latest

    return extracted


def compute_missing_fields(
    collected_fields: dict[str, Any],
    messages: list[dict[str, Any]],
    request_type: str,
) -> list[str]:
    """Return fields still missing after considering explicit user input."""
    mapped = dict(collected_fields)
    required = get_intake_required_fields(request_type)
    full_text = _conversation_text(messages)

    if get_intake_search_corpus() == "amtech-demo":
        if not mapped.get("module") and mapped.get("system"):
            mapped["module"] = mapped["system"]
        if not mapped.get("description"):
            mapped["description"] = (
                mapped.get("actual_behavior")
                or mapped.get("summary")
                or (full_text if len(_user_messages(messages)) == 1 else None)
            )
        env = normalize_coderoad_environment(mapped.get("environment"), full_text)
        if env:
            mapped["environment"] = env
        else:
            mapped.pop("environment", None)
        if not mapped.get("identifier"):
            mapped["identifier"] = _explicit_identifier(full_text)
        if not mapped.get("identifier") and mapped.get("description"):
            mapped["identifier"] = str(mapped["description"])[:120]
        required = ["module", "identifier", "description", "environment"]
    else:
        if not mapped.get("actual_behavior") and len(_user_messages(messages)) == 1:
            mapped["actual_behavior"] = full_text or None
        env = normalize_coderoad_environment(mapped.get("environment"), full_text)
        if env:
            mapped["environment"] = env
        else:
            mapped.pop("environment", None)
        if not mapped.get("identifier"):
            mapped["identifier"] = _explicit_identifier(full_text)

    missing: list[str] = []
    for field in required:
        val = mapped.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing


def get_field_options_for_missing(missing_fields: list[str]) -> dict[str, list[dict[str, str]]]:
    options: dict[str, list[dict[str, str]]] = {}
    for field in missing_fields:
        if field in FIELD_OPTIONS:
            options[field] = FIELD_OPTIONS[field]
        elif field == "system":
            options["system"] = FIELD_OPTIONS["module"]
    return options


def build_intake_batch_follow_up(
    *,
    request_type: str,
    missing_fields: list[str],
    understood: str,
) -> str:
    """One message listing every missing field."""
    if not missing_fields:
        return ""

    cfg = get_global_config()
    intro = cfg.get(
        "batch_fields_intro",
        "Please provide **all** of the following in one message:",
    )
    footer = cfg.get(
        "batch_fields_footer",
        "You can reply in a single message with all of the information above, "
        "or use the quick-select buttons below.",
    )

    lines: list[str] = []
    for i, field in enumerate(missing_fields, 1):
        prompt = FIELD_PROMPTS.get(field)
        if not prompt:
            question = get_follow_up_question(request_type, field)
            prompt = f"**{format_field_label(field)}** — {question}"
        lines.append(f"{i}. {prompt}")

    return (
        f"Thank you for reaching out. I have registered **{understood}**.\n\n"
        f"{intro}\n\n"
        + "\n".join(lines)
        + f"\n\n{footer}"
    )


def ui_hints_for_collection(state_missing: list[str]) -> dict[str, Any]:
    return {
        "awaitingFields": state_missing,
        "fieldOptions": get_field_options_for_missing(state_missing),
    }
