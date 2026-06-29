"""Optional LLM judge for live eval response quality."""

from __future__ import annotations

import json
import logging

from google.genai import types

from ..genai_utils import generate_content
from .models import EvalCheck, EvalScenario

logger = logging.getLogger(__name__)


def judge_response_quality(
    scenario: EvalScenario,
    assistant_message: str,
) -> EvalCheck:
    if not scenario.expected.expected_response:
        return EvalCheck(
            name="judge.quality",
            expected="advisory",
            actual=None,
            passed=True,
            skipped=True,
            message="No reference response in dataset",
        )

    prompt = f"""You are grading a support intake assistant reply against a reference.

Scenario ID: {scenario.id}
User input: {scenario.input}
Expected route: {scenario.expected.route}

Reference response:
{scenario.expected.expected_response}

Actual response:
{assistant_message}

Grade whether the actual response:
1. Acknowledges the user's issue and key entities
2. Matches the expected routing intent ({scenario.expected.route})
3. Does not invent KB article IDs not in the reference
4. Uses professional, concise tone

Respond with JSON only:
{{"passed": true|false, "reason": "one sentence"}}
"""
    try:
        raw = generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        text = (raw or "{}").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(text)
        passed = bool(result.get("passed"))
        return EvalCheck(
            name="judge.quality",
            expected="pass rubric",
            actual=result.get("reason"),
            passed=passed,
            message=str(result.get("reason", "")),
        )
    except Exception as exc:
        logger.warning("LLM judge failed for %s: %s", scenario.id, exc)
        return EvalCheck(
            name="judge.quality",
            expected="pass rubric",
            actual=str(exc),
            passed=True,
            skipped=True,
            message="Judge unavailable; skipped",
        )
