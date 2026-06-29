"""Layer 1 heuristic evals for all Amtech scenarios."""

from __future__ import annotations

import pytest

from support_intake.evals.dataset import load_scenarios
from support_intake.evals.runner import run_layer1


@pytest.mark.parametrize(
    "scenario",
    load_scenarios(),
    ids=lambda scenario: scenario.id,
)
def test_layer1_heuristics(scenario) -> None:
    case = run_layer1(scenario)
    failed = [check for check in case.checks if not check.passed and not check.skipped]
    assert case.passed, (
        f"Scenario {scenario.id} failed: "
        + "; ".join(
            f"{check.name} expected={check.expected} actual={check.actual}"
            for check in failed
        )
    )
