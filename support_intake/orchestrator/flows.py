"""Three-flow intake classification (feature / known bug / unknown bug)."""

from __future__ import annotations

from typing import Any

from ..config_loader import get_request_type_config, load_intake_config

FLOW_FEATURE = "flow_1"
FLOW_KNOWN_BUG = "flow_2"
FLOW_UNKNOWN_BUG = "flow_3"

_REQUEST_TO_FLOW: dict[str, str] = {
    "feature_request": FLOW_FEATURE,
    "known_issue": FLOW_KNOWN_BUG,
    "faq": FLOW_KNOWN_BUG,
    "technical_incident": FLOW_UNKNOWN_BUG,
    "unclear": FLOW_UNKNOWN_BUG,
    "unsupported": FLOW_UNKNOWN_BUG,
    "access_request": FLOW_UNKNOWN_BUG,
}


def get_flow_id(request_type: str) -> str:
    return _REQUEST_TO_FLOW.get(request_type, FLOW_UNKNOWN_BUG)


def get_flow_config(request_type: str) -> dict[str, Any]:
    flow_id = get_flow_id(request_type)
    flows = load_intake_config().get("flows", {})
    return flows.get(flow_id, {})


def get_flow_label(request_type: str) -> str:
    cfg = get_flow_config(request_type)
    return str(cfg.get("label", get_flow_id(request_type)))


def should_attempt_kb_resolution(request_type: str) -> bool:
    """Flow 2 searches KB; Flow 1 and 3 go straight to ticket path."""
    from ..adapters.knowledge_hub import get_intake_search_corpus

    if get_intake_search_corpus() == "amtech-demo":
        if request_type in ("technical_incident", "known_issue", "faq", "unclear"):
            return True

    cfg = get_flow_config(request_type)
    if "try_kb" in cfg:
        return bool(cfg["try_kb"])
    type_cfg = get_request_type_config(request_type)
    return bool(type_cfg.get("auto_answer_allowed", False))


def should_skip_kb_for_request(request_type: str) -> bool:
    return not should_attempt_kb_resolution(request_type)


def estimate_ticket_time(request_type: str) -> str:
    """Rough placeholder estimate shown on tickets (planning concept)."""
    cfg = get_flow_config(request_type)
    if cfg.get("default_estimate"):
        return str(cfg["default_estimate"])
    estimates = {
        "feature_request": "16h (rough)",
        "known_issue": "4h (rough)",
        "faq": "2h (rough)",
        "technical_incident": "8h (rough)",
        "unclear": "6h (rough)",
        "unsupported": "8h (rough)",
        "access_request": "2h (rough)",
    }
    return estimates.get(request_type, "4h (rough)")


def classification_notice(request_type: str) -> str:
    label = get_flow_label(request_type)
    cfg = get_flow_config(request_type)
    summary = str(cfg.get("summary", "")).strip()
    if summary:
        return f"**{label}** — {summary}"
    return f"**{label}**"
