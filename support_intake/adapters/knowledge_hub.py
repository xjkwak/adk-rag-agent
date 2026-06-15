"""Knowledge Hub adapter — wraps existing rag_query for intake search."""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from knowledge_hub.tools.rag_query import rag_query

from ..config import (
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_GENAI_USE_VERTEXAI,
    INTAKE_KB_CONFIDENCE_THRESHOLD,
    NLU_MODEL,
    SUPPORT_KB_CORPUS,
)
from ..config_loader import get_global_config
from ..orchestrator.state import KnowledgeResult

logger = logging.getLogger(__name__)


class _IntakeToolContext:
    def __init__(self) -> None:
        self.state: dict[str, Any] = {"current_corpus": SUPPORT_KB_CORPUS}


def build_search_query(collected_fields: dict[str, Any], original_message: str | None) -> str:
    parts = []
    for key in ("summary", "system", "actual_behavior", "error_message", "expected_behavior"):
        val = collected_fields.get(key)
        if val:
            parts.append(str(val))
    if not parts and original_message:
        parts.append(original_message)
    return " ".join(parts) if parts else "support request"


def search_knowledge_hub(
    collected_fields: dict[str, Any],
    original_message: str | None = None,
) -> tuple[list[KnowledgeResult], float]:
    query = build_search_query(collected_fields, original_message)
    ctx = _IntakeToolContext()
    result = rag_query(SUPPORT_KB_CORPUS, query, ctx)

    if result.get("status") != "success":
        logger.info("KB search returned no success: %s", result.get("message"))
        return [], 0.0

    raw_results = result.get("results", [])
    knowledge_results: list[KnowledgeResult] = []
    top_score = 0.0

    for r in raw_results:
        score = float(r.get("score", 0.0))
        kr = KnowledgeResult(
            source_name=r.get("source_name", ""),
            source_uri=r.get("source_uri", ""),
            text=r.get("text", ""),
            score=score,
        )
        knowledge_results.append(kr)
        top_score = max(top_score, score)

    return knowledge_results, top_score


def meets_confidence_threshold(top_score: float, result_count: int) -> bool:
    global_cfg = get_global_config()
    threshold = float(
        global_cfg.get("knowledge_confidence_threshold", INTAKE_KB_CONFIDENCE_THRESHOLD)
    )
    min_results = int(global_cfg.get("knowledge_min_results", 1))
    return top_score >= threshold and result_count >= min_results


def generate_grounded_answer(
    query: str,
    knowledge_results: list[KnowledgeResult],
) -> str:
    if not knowledge_results:
        return ""

    context_chunks = []
    for i, r in enumerate(knowledge_results[:5], 1):
        context_chunks.append(
            f"[Source {i}: {r.source_name}]\n{r.text}\n"
        )
    context = "\n---\n".join(context_chunks)

    prompt = f"""You are a support assistant. Answer the user's question using ONLY the retrieved Knowledge Hub content below.
If the content does not clearly address the question, say you could not find a definitive answer.
Include actionable steps when available.
Cite source names.

User question / context: {query}

Retrieved content:
{context}

Provide a concise, helpful answer with resolution steps.
"""
    if GOOGLE_GENAI_USE_VERTEXAI:
        client = genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
        )
    else:
        client = genai.Client()

    response = client.models.generate_content(
        model=NLU_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return (response.text or "").strip()
