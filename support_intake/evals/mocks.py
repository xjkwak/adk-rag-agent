"""KB and NLU mocks for deterministic integration evals."""

from __future__ import annotations

import re
from typing import Any

from ..orchestrator.state import KnowledgeResult
from .models import EvalScenario

_KB_ANSWERS: dict[str, str] = {
    "KB-002": (
        "This matches KB-002 (PDF / Report Generation Failure). "
        "Allow pop-ups for CoderoadERP and retry the download."
    ),
    "KB-003": (
        "This matches KB-003 (Greyed-Out / Inactive Button). "
        "Check Permissions & Authorization Levels and request temporary elevation."
    ),
    "KB-004": (
        "This matches KB-004 (Credit Limit Block). "
        "Review Customer Accounts → Credit & Aging Status."
    ),
    "KB-005": (
        "This matches KB-005 (Thermal Printer Routing Failure). "
        "Set Default Printer Destination to Direct Network IP."
    ),
    "KB-006": (
        "Batch RB-9902 is displaying a stale database row lock in CoderoadOPS TEST. "
        "This matches KB-006 (Stuck Roll Stock / Database Row Lock). "
        "Navigate to Active Session Monitor and Force Clear Stale Row Locks."
    ),
    "KB-007": (
        "Unlock Account for the locked employee in Administration Console → Security. "
        "This matches KB-007 (User Account Lockout)."
    ),
    "KB-009": (
        "Exit Code 2 on the nightly backup job means partial execution. "
        "This matches KB-009 (Scheduled Job Partial Execution). "
        "Review the Execution Log and run Manual Re-Run."
    ),
    "KB-010": (
        "This matches KB-010 (Contract Price Table Mismatch). "
        "Assign the correct contract and Recalculate Prices."
    ),
    "KB-012": (
        "This matches KB-012 (Dashboard KPI Panel Not Loading). "
        "Clear browser cache and cookies for CoderoadERP."
    ),
}


def kb_answer_for_scenario(scenario: EvalScenario) -> str:
    kb = scenario.expected.kb_article or ""
    if kb in _KB_ANSWERS:
        base = _KB_ANSWERS[kb]
    else:
        phrases = "\n".join(
            f"- {phrase}" for phrase in scenario.expected.response_must_include
        )
        base = f"This matches {kb}.\n{phrases}"
    identifier = scenario.expected.entities.get("identifier")
    extras = re.findall(
        r"\b(?:INV|PO|RB|CUS|GD|FG|PR|SO|EMP)-\d+\b",
        scenario.input,
        flags=re.IGNORECASE,
    )
    refs: list[str] = []
    if identifier and identifier.lower() != "missing":
        refs.append(identifier)
    for token in extras:
        upper = token.upper()
        if upper not in refs:
            refs.append(upper)
    if refs:
        return f"{base} References: {', '.join(refs)}."
    return base


def mock_search_knowledge_hub(
    scenario: EvalScenario,
    collected_fields: dict[str, Any],
    original_message: str | None,
) -> tuple[list[KnowledgeResult], float]:
    kb = scenario.expected.kb_article
    if not kb:
        return [], 0.0
    text = kb_answer_for_scenario(scenario)
    result = KnowledgeResult(
        source_name="KB.md",
        source_uri="amtech-demo/KB.md",
        text=f"{kb}: {text}",
        score=0.95,
    )
    return [result], 0.95


def mock_generate_grounded_answer(
    scenario: EvalScenario,
    query: str,
    results: list[KnowledgeResult],
) -> str:
    del query, results
    return kb_answer_for_scenario(scenario)


def mock_extract_fields(
    messages: list[dict[str, str]],
    request_type: str,
    field_names: list[str],
    existing: dict[str, Any],
) -> dict[str, Any]:
    from ..orchestrator.field_heuristics import extract_coderoad_fields_heuristic
    from ..orchestrator.intake_fields import extract_explicit_fields

    merged = dict(existing)
    for key, value in extract_explicit_fields(messages, field_names, merged).items():
        if value is not None:
            merged[key] = value
    for key, value in extract_coderoad_fields_heuristic(
        messages, merged, field_names
    ).items():
        if value is not None:
            merged[key] = value
    if merged.get("module") and not merged.get("system"):
        merged["system"] = merged["module"]
    return {
        name: merged[name]
        for name in field_names
        if name in merged and merged[name] not in (None, "")
    }


def classify_request_for_scenario(scenario: EvalScenario) -> str:
    route = scenario.expected.route
    if route == "route_a":
        return "known_issue"
    return "technical_incident"
