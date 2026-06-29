"""Optional live evals against real LLM + KB."""

from __future__ import annotations

import os

import pytest

from support_intake.evals.dataset import load_scenarios
from support_intake.evals.models import EvalMode
from support_intake.evals.runner import run_scenario

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def live_enabled() -> None:
    if os.environ.get("RUN_LIVE_EVALS") != "1":
        pytest.skip("Set RUN_LIVE_EVALS=1 to run live evals")


@pytest.mark.parametrize(
    "scenario",
    load_scenarios(),
    ids=lambda scenario: scenario.id,
)
@pytest.mark.asyncio
async def test_layer3_live(scenario, live_enabled) -> None:
    del live_enabled
    case = await run_scenario(scenario, EvalMode.LIVE)
    failed = [check for check in case.checks if not check.passed and not check.skipped]
    assert case.passed, (
        f"Scenario {scenario.id} failed: "
        + "; ".join(f"{check.name} expected={check.expected} actual={check.actual}" for check in failed)
    )
