#!/usr/bin/env python3
"""Validate Amtech scenario YAML against Testing Framework markdown."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "assets" / "Amtech" / "Testing_Framework.md"
YAML_PATH = ROOT / "support_intake" / "evals" / "datasets" / "amtech_scenarios.yaml"


def _scenario_ids_from_markdown(text: str) -> list[str]:
    return re.findall(r"### Scenario (\d+\.\d+)", text)


def main() -> int:
    md = MD_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    md_ids = _scenario_ids_from_markdown(md)
    yaml_ids = [str(item["id"]) for item in data.get("scenarios", [])]

    missing = sorted(set(md_ids) - set(yaml_ids))
    extra = sorted(set(yaml_ids) - set(md_ids))

    print(f"Markdown scenarios: {len(md_ids)}")
    print(f"YAML scenarios:     {len(yaml_ids)}")
    if missing:
        print("Missing in YAML:", ", ".join(missing))
    if extra:
        print("Extra in YAML:", ", ".join(extra))

    return 0 if not missing and len(yaml_ids) == 25 else 1


if __name__ == "__main__":
    raise SystemExit(main())
