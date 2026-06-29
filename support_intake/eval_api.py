"""FastAPI routes for Support Intake eval runs."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .evals.dataset import get_scenario, load_scenarios
from .evals.models import EvalMode
from .evals.runner import run_eval_suite

router = APIRouter()


class EvalRunRequest(BaseModel):
    mode: Literal["fast", "integration", "live"] = "integration"
    scenario_ids: list[str] | None = None


@router.get("/evals/scenarios")
async def list_eval_scenarios() -> dict[str, Any]:
    scenarios = load_scenarios()
    return {
        "total": len(scenarios),
        "scenarios": [scenario.to_summary_dict() for scenario in scenarios],
    }


@router.get("/evals/scenarios/{scenario_id}")
async def get_eval_scenario(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.to_detail_dict()


@router.post("/evals/run")
async def run_evals(body: EvalRunRequest) -> dict[str, Any]:
    mode = EvalMode(body.mode)
    result = await run_eval_suite(mode, body.scenario_ids)
    return result.to_dict()
