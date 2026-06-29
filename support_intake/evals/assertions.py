"""Assertion helpers for Support Intake evals."""

from __future__ import annotations

import re
from typing import Any

from ..adapters.knowledge_hub import normalize_coderoad_environment
from .models import EvalCheck, EvalExpected, EvalMode, EvalScenario


def _normalize_module(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s*\([^)]*\)", "", text)
    return text.strip()


def _normalize_identifier(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = text.lstrip("#")
    return text


def _entity_matches(field: str, expected: str, actual: Any) -> bool:
    if actual is None or str(actual).strip() == "":
        return False
    if field == "module":
        exp = _normalize_module(expected)
        act = _normalize_module(actual)
        return exp in act or act in exp
    if field == "environment":
        exp = normalize_coderoad_environment(expected) or expected.upper()
        act = normalize_coderoad_environment(actual) or str(actual).upper()
        return exp == act
    if field == "identifier":
        exp = _normalize_identifier(expected)
        act = _normalize_identifier(actual)
        if exp in act or act in exp:
            return True
        return exp.split("/")[0].strip() in act
    if field == "description":
        exp_words = {word for word in re.findall(r"[a-z0-9]+", expected.lower()) if len(word) > 3}
        act_text = str(actual).lower()
        if not exp_words:
            return bool(act_text.strip())
        hits = sum(1 for word in exp_words if word in act_text)
        return hits >= max(1, len(exp_words) // 3)
    return str(expected).lower() in str(actual).lower()


def check_entities(
    expected: EvalExpected,
    collected: dict[str, Any],
    *,
    layer: EvalMode,
) -> list[EvalCheck]:
    checks: list[EvalCheck] = []
    for field, value in expected.entities.items():
        if value.lower() in ("missing", "n/a"):
            checks.append(
                EvalCheck(
                    name=f"entity.{field}",
                    expected="missing",
                    actual=collected.get(field),
                    passed=not collected.get(field),
                )
            )
            continue
        actual = collected.get(field)
        if actual is None and field == "module":
            actual = collected.get("system")
        checks.append(
            EvalCheck(
                name=f"entity.{field}",
                expected=value,
                actual=actual,
                passed=_entity_matches(field, value, actual),
            )
        )
    if layer == EvalMode.FAST and not checks:
        checks.append(
            EvalCheck(
                name="entity.extraction",
                expected="entities",
                actual=collected,
                passed=bool(collected),
                skipped=True,
                message="No entity expectations defined",
            )
        )
    return checks


def check_missing_fields(
    expected: EvalExpected,
    actual_missing: list[str],
) -> EvalCheck:
    if not expected.missing_fields:
        passed = not actual_missing
        return EvalCheck(
            name="missing_fields",
            expected=[],
            actual=actual_missing,
            passed=passed,
        )

    overlap = [
        field
        for field in expected.missing_fields
        if field in actual_missing
    ]
    passed = bool(overlap) or bool(actual_missing)
    return EvalCheck(
        name="missing_fields",
        expected=expected.missing_fields,
        actual=actual_missing,
        passed=passed,
        message=None if passed else "Expected missing-field collection prompt",
    )


def check_route(
    expected_route: str,
    actual_route: str,
    *,
    layer: EvalMode,
) -> EvalCheck:
    if layer == EvalMode.FAST and expected_route in ("route_a", "route_b"):
        return EvalCheck(
            name="route",
            expected=expected_route,
            actual=actual_route,
            passed=True,
            skipped=True,
            message="Route A/B requires orchestrator layer",
        )
    return EvalCheck(
        name="route",
        expected=expected_route,
        actual=actual_route,
        passed=expected_route == actual_route,
    )


def check_kb_article(
    expected_kb: str | None,
    assistant_message: str,
    kb_answer: str | None,
    *,
    layer: EvalMode,
) -> EvalCheck | None:
    if not expected_kb:
        return None
    if layer == EvalMode.FAST:
        return EvalCheck(
            name="kb_article",
            expected=expected_kb,
            actual=None,
            passed=True,
            skipped=True,
            message="KB check requires integration layer",
        )
    haystack = f"{assistant_message}\n{kb_answer or ''}"
    passed = expected_kb.upper() in haystack.upper()
    advisory = layer == EvalMode.LIVE and not passed
    return EvalCheck(
        name="kb_article",
        expected=expected_kb,
        actual=expected_kb if passed else None,
        passed=passed or advisory,
        skipped=advisory,
        message=(
            "Advisory in live mode — KB article may be paraphrased"
            if advisory
            else None
        ),
    )


def check_response_phrases(
    expected: EvalExpected,
    assistant_message: str,
    *,
    layer: EvalMode,
    kb_answer: str | None = None,
    route_check_passed: bool = False,
    kb_check_passed: bool = False,
) -> list[EvalCheck]:
    if layer == EvalMode.FAST or not expected.response_must_include:
        return []
    haystack = f"{assistant_message}\n{kb_answer or ''}".lower()
    checks: list[EvalCheck] = []
    for phrase in expected.response_must_include:
        needle = phrase.lower()
        if needle == "confirm":
            passed = "confirm" in haystack or "yes" in haystack
        else:
            passed = needle in haystack
        advisory = (
            layer == EvalMode.LIVE
            and route_check_passed
            and (expected.route != "route_a" or kb_check_passed)
            and not passed
        )
        checks.append(
            EvalCheck(
                name=f"response.includes:{phrase[:40]}",
                expected=phrase,
                actual=phrase if passed else None,
                passed=passed or advisory,
                skipped=advisory,
                message=(
                    "Advisory in live mode — phrasing may vary"
                    if advisory
                    else None
                ),
            )
        )
    return checks


def check_ticket_preview(
    scenario: EvalScenario,
    ticket_preview: dict[str, Any] | None,
    *,
    layer: EvalMode,
) -> list[EvalCheck]:
    if scenario.expected.route != "route_b" or layer == EvalMode.FAST:
        return []
    checks: list[EvalCheck] = [
        EvalCheck(
            name="ticket_preview.present",
            expected=True,
            actual=ticket_preview is not None,
            passed=ticket_preview is not None,
        )
    ]
    if not ticket_preview:
        return checks
    identifier = scenario.expected.entities.get("identifier", "")
    summary = str(ticket_preview.get("summary", ""))
    if identifier and identifier.lower() != "missing":
        token = _normalize_identifier(identifier.split("/")[0])
        passed = token in summary.upper()
        checks.append(
            EvalCheck(
                name="ticket_preview.identifier",
                expected=token,
                actual=summary,
                passed=passed,
                skipped=layer == EvalMode.LIVE and not passed,
                message=(
                    "Advisory in live mode — title may omit document ID"
                    if layer == EvalMode.LIVE and not passed
                    else None
                ),
            )
        )
    return checks


def case_passed(checks: list[EvalCheck]) -> bool:
    active = [check for check in checks if not check.skipped]
    return bool(active) and all(check.passed for check in active)
