"""Layer 2 orchestrator evals with mocked KB."""

from __future__ import annotations

import pytest

from support_intake.evals.dataset import load_scenarios
from support_intake.evals.models import EvalMode
from support_intake.evals.runner import run_scenario


@pytest.mark.parametrize(
    "scenario",
    load_scenarios(),
    ids=lambda scenario: scenario.id,
)
@pytest.mark.asyncio
async def test_layer2_orchestrator(scenario) -> None:
    case = await run_scenario(scenario, EvalMode.INTEGRATION)
    failed = [check for check in case.checks if not check.passed and not check.skipped]
    assert case.passed, (
        f"Scenario {scenario.id} failed: "
        + "; ".join(f"{check.name} expected={check.expected} actual={check.actual}" for check in failed)
    )
