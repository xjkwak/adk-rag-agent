"""Load Amtech eval scenarios from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import EvalExpected, EvalScenario

_DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "amtech_scenarios.yaml"


def dataset_path() -> Path:
    return _DATASET_PATH


def load_scenarios(scenario_ids: list[str] | None = None) -> list[EvalScenario]:
    raw = yaml.safe_load(_DATASET_PATH.read_text(encoding="utf-8"))
    scenarios: list[EvalScenario] = []
    for item in raw.get("scenarios", []):
        expected_raw = item.get("expected", {})
        expected = EvalExpected(
            route=str(expected_raw.get("route", "")),
            entities=dict(expected_raw.get("entities") or {}),
            kb_article=expected_raw.get("kb_article"),
            missing_fields=list(expected_raw.get("missing_fields") or []),
            response_must_include=list(
                expected_raw.get("response_must_include") or []
            ),
            expected_response=expected_raw.get("expected_response"),
        )
        scenario = EvalScenario(
            id=str(item["id"]),
            role=str(item.get("role", "")),
            title=str(item.get("title", "")),
            input=str(item.get("input", "")),
            modality=str(item.get("modality", "text")),
            expected=expected,
        )
        scenarios.append(scenario)

    if scenario_ids:
        wanted = set(scenario_ids)
        scenarios = [scenario for scenario in scenarios if scenario.id in wanted]
    return scenarios


def get_scenario(scenario_id: str) -> EvalScenario | None:
    for scenario in load_scenarios():
        if scenario.id == scenario_id:
            return scenario
    return None
