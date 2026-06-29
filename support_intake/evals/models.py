"""Data models for Support Intake eval runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvalMode(str, Enum):
    FAST = "fast"
    INTEGRATION = "integration"
    LIVE = "live"


@dataclass
class EvalExpected:
    route: str
    entities: dict[str, str] = field(default_factory=dict)
    kb_article: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    response_must_include: list[str] = field(default_factory=list)
    expected_response: str | None = None


@dataclass
class EvalScenario:
    id: str
    role: str
    title: str
    input: str
    modality: str = "text"
    expected: EvalExpected = field(default_factory=EvalExpected)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "title": self.title,
            "expectedRoute": self.expected.route,
            "modality": self.modality,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        return {
            **self.to_summary_dict(),
            "input": self.input,
            "expected": {
                "route": self.expected.route,
                "entities": self.expected.entities,
                "kbArticle": self.expected.kb_article,
                "missingFields": self.expected.missing_fields,
                "responseMustInclude": self.expected.response_must_include,
                "expectedResponse": self.expected.expected_response,
            },
        }


@dataclass
class EvalCheck:
    name: str
    expected: Any
    actual: Any
    passed: bool
    skipped: bool = False
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "skipped": self.skipped,
            "message": self.message,
        }


@dataclass
class EvalCaseResult:
    id: str
    passed: bool
    checks: list[EvalCheck] = field(default_factory=list)
    actual: dict[str, Any] = field(default_factory=dict)
    skipped: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "passed": self.passed,
            "skipped": self.skipped,
            "error": self.error,
            "checks": [check.to_dict() for check in self.checks],
            "actual": self.actual,
        }


@dataclass
class EvalRunSummary:
    total: int
    passed: int
    failed: int
    skipped: int

    def to_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


@dataclass
class EvalRunResult:
    run_id: str
    mode: EvalMode
    started_at: str
    duration_ms: int
    summary: EvalRunSummary
    cases: list[EvalCaseResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "runId": self.run_id,
            "mode": self.mode.value,
            "startedAt": self.started_at,
            "durationMs": self.duration_ms,
            "summary": self.summary.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
        }
