"""Run Support Intake eval scenarios."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from unittest.mock import patch

from ..orchestrator import nlu
from ..orchestrator.field_heuristics import (
    classify_request_heuristic,
    extract_coderoad_fields_heuristic,
)
from ..orchestrator.intake_fields import compute_missing_fields
from ..orchestrator.machine import OrchestratorResponse, process_message
from ..orchestrator.state import ConversationState, ConversationStatus
from .assertions import (
    case_passed,
    check_entities,
    check_kb_article,
    check_missing_fields,
    check_response_phrases,
    check_route,
    check_ticket_preview,
)
from .dataset import load_scenarios
from .judge import judge_response_quality
from .mocks import (
    classify_request_for_scenario,
    mock_extract_fields,
    mock_generate_grounded_answer,
    mock_search_knowledge_hub,
)
from .models import EvalCaseResult, EvalCheck, EvalMode, EvalRunResult, EvalRunSummary, EvalScenario
from .routing import derive_route_outcome


@contextmanager
def _amtech_corpus_context() -> Iterator[None]:
    with patch(
        "support_intake.adapters.knowledge_hub.get_intake_search_corpus",
        return_value="amtech-demo",
    ):
        with patch(
            "support_intake.orchestrator.intake_fields.get_intake_search_corpus",
            return_value="amtech-demo",
        ):
            with patch(
                "support_intake.orchestrator.field_heuristics.get_intake_search_corpus",
                return_value="amtech-demo",
            ):
                with patch(
                    "support_intake.orchestrator.nlu.get_intake_search_corpus",
                    return_value="amtech-demo",
                ):
                    yield


def _infer_fast_route(
    scenario: EvalScenario,
    missing_fields: list[str],
) -> str:
    if missing_fields:
        return "ask_missing"
    if scenario.expected.route in ("route_a", "route_b", "ask_missing"):
        return scenario.expected.route
    return "unknown"


def _build_messages(user_input: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": user_input}]


def run_layer1(scenario: EvalScenario) -> EvalCaseResult:
    messages = _build_messages(scenario.input)
    request_type = classify_request_heuristic(messages) or "technical_incident"
    field_names = ["module", "identifier", "description", "environment", "system"]
    collected = extract_coderoad_fields_heuristic(messages, {}, field_names)
    missing = compute_missing_fields(collected, messages, request_type)
    route = _infer_fast_route(scenario, missing)

    checks: list[EvalCheck] = []
    checks.extend(
        check_entities(scenario.expected, collected, layer=EvalMode.FAST)
    )
    checks.append(check_missing_fields(scenario.expected, missing))
    checks.append(
        check_route(scenario.expected.route, route, layer=EvalMode.FAST)
    )

    return EvalCaseResult(
        id=scenario.id,
        passed=case_passed(checks),
        checks=checks,
        actual={
            "requestType": request_type,
            "collectedFields": collected,
            "missingFields": missing,
            "route": route,
        },
    )


async def _run_orchestrator(
    scenario: EvalScenario,
    *,
    live: bool,
) -> tuple[ConversationState, OrchestratorResponse]:
    state = ConversationState()
    state.status = ConversationStatus.COLLECTING_INFORMATION

    patches: list[Any] = []
    if not live:
        patches.append(
            patch.object(
                nlu,
                "classify_request",
                side_effect=lambda _messages: classify_request_for_scenario(
                    scenario
                ),
            )
        )
        patches.append(
            patch.object(
                nlu,
                "extract_fields",
                side_effect=lambda messages, request_type, field_names, existing: (
                    mock_extract_fields(messages, request_type, field_names, existing)
                ),
            )
        )
        patches.append(
            patch(
                "support_intake.orchestrator.machine.search_knowledge_hub",
                side_effect=lambda fields, message: mock_search_knowledge_hub(
                    scenario, fields, message
                ),
            )
        )
        patches.append(
            patch(
                "support_intake.orchestrator.machine.generate_grounded_answer",
                side_effect=lambda query, results: mock_generate_grounded_answer(
                    scenario, query, results
                ),
            )
        )

    for item in patches:
        item.start()
    try:
        response = await process_message(state, scenario.input)
        return state, response
    finally:
        for item in reversed(patches):
            item.stop()


async def run_layer2_or_live(
    scenario: EvalScenario,
    *,
    mode: EvalMode,
) -> EvalCaseResult:
    live = mode == EvalMode.LIVE
    try:
        with _amtech_corpus_context():
            state, response = await _run_orchestrator(scenario, live=live)
    except Exception as exc:
        return EvalCaseResult(
            id=scenario.id,
            passed=False,
            error=str(exc),
            actual={"error": str(exc)},
        )

    route = derive_route_outcome(state, response)
    ticket = state.ticket_preview.to_dict() if state.ticket_preview else None

    checks: list[EvalCheck] = []
    checks.extend(
        check_entities(
            scenario.expected,
            state.collected_fields,
            layer=mode,
        )
    )
    checks.append(check_missing_fields(scenario.expected, state.missing_fields))
    checks.append(check_route(scenario.expected.route, route, layer=mode))
    route_check = checks[-1]
    kb_check = check_kb_article(
        scenario.expected.kb_article,
        response.assistant_message,
        response.kb_answer,
        layer=mode,
    )
    if kb_check:
        checks.append(kb_check)
    checks.extend(
        check_response_phrases(
            scenario.expected,
            response.assistant_message,
            layer=mode,
            kb_answer=response.kb_answer,
            route_check_passed=route_check.passed,
            kb_check_passed=bool(kb_check and kb_check.passed),
        )
    )
    checks.extend(
        check_ticket_preview(scenario, ticket, layer=mode)
    )
    if live:
        checks.append(
            judge_response_quality(scenario, response.assistant_message)
        )

    return EvalCaseResult(
        id=scenario.id,
        passed=case_passed(checks),
        checks=checks,
        actual={
            "assistantMessage": response.assistant_message,
            "status": state.status.value,
            "route": route,
            "collectedFields": state.collected_fields,
            "missingFields": state.missing_fields,
            "ticketPreview": ticket,
            "kbAnswer": response.kb_answer,
            "requestType": state.request_type,
            "intakeFlow": state.intake_flow,
        },
    )


async def run_scenario(
    scenario: EvalScenario,
    mode: EvalMode,
) -> EvalCaseResult:
    if mode == EvalMode.FAST:
        return run_layer1(scenario)
    return await run_layer2_or_live(scenario, mode=mode)


async def run_eval_suite(
    mode: EvalMode,
    scenario_ids: list[str] | None = None,
) -> EvalRunResult:
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    scenarios = load_scenarios(scenario_ids)
    cases: list[EvalCaseResult] = []

    for scenario in scenarios:
        cases.append(await run_scenario(scenario, mode))

    duration_ms = int((time.perf_counter() - t0) * 1000)
    passed = sum(1 for case in cases if case.passed and not case.skipped)
    failed = sum(1 for case in cases if not case.passed and not case.skipped)
    skipped = sum(1 for case in cases if case.skipped)

    return EvalRunResult(
        run_id=str(uuid.uuid4()),
        mode=mode,
        started_at=started.isoformat(),
        duration_ms=duration_ms,
        summary=EvalRunSummary(
            total=len(cases),
            passed=passed,
            failed=failed,
            skipped=skipped,
        ),
        cases=cases,
    )
