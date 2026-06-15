"""Load and expose intake workflow configuration from YAML."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "intake_rules.yaml"


@lru_cache(maxsize=1)
def load_intake_config() -> dict[str, Any]:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_request_types() -> dict[str, Any]:
    return load_intake_config().get("request_types", {})


def get_request_type_config(request_type: str) -> dict[str, Any]:
    types = get_request_types()
    if request_type not in types:
        return types.get("unclear", {})
    return types[request_type]


def get_global_config() -> dict[str, Any]:
    return load_intake_config().get("global", {})


def get_jira_config() -> dict[str, Any]:
    return load_intake_config().get("jira", {})


def get_follow_up_question(request_type: str, field: str) -> str:
    cfg = get_request_type_config(request_type)
    questions = cfg.get("follow_up_questions", {})
    return questions.get(field, f"Please provide: {field.replace('_', ' ')}.")


def format_field_label(field: str) -> str:
    return field.replace("_", " ").strip().title()


def get_batch_follow_up_message(request_type: str, missing_fields: list[str]) -> str:
    """Build one message listing every missing required field."""
    if not missing_fields:
        return ""

    cfg = get_global_config()
    intro = cfg.get(
        "batch_fields_intro",
        "I couldn't find a complete answer in our Knowledge Hub. "
        "To create a support ticket, please provide the following:",
    )
    lines = [
        f"{i}. **{format_field_label(field)}** — {get_follow_up_question(request_type, field)}"
        for i, field in enumerate(missing_fields, 1)
    ]
    footer = cfg.get(
        "batch_fields_footer",
        "You can reply in a single message with all of the information above.",
    )
    return f"{intro}\n\n" + "\n".join(lines) + f"\n\n{footer}"


def get_required_fields(request_type: str) -> list[str]:
    return list(get_request_type_config(request_type).get("required_fields", []))


def get_optional_fields(request_type: str) -> list[str]:
    return list(get_request_type_config(request_type).get("optional_fields", []))
