"""Knowledge Hub adapter — wraps existing rag_query for intake search."""

from __future__ import annotations

import logging
import re
from typing import Any

from google.genai import types
from knowledge_hub.tools.rag_query import rag_query

from ..config import INTAKE_KB_CONFIDENCE_THRESHOLD, SUPPORT_KB_CORPUS
from ..config_loader import format_field_label, get_global_config
from ..genai_utils import generate_content
from ..orchestrator.state import KnowledgeResult

logger = logging.getLogger(__name__)

_NO_ANSWER_MARKERS = (
    "could not find a definitive answer",
    "couldn't find a definitive answer",
    "does not clearly address",
    "doesn't clearly address",
    "no definitive answer",
    "unable to find",
    "cannot find a definitive answer",
    "can't find a definitive answer",
)


def get_intake_search_corpus() -> str:
    """Corpus for intake KB search — matches Configuration default corpus."""
    try:
        from knowledge_hub.settings_store import get_default_corpus

        corpus = get_default_corpus().strip()
        if corpus:
            return corpus
    except Exception:
        logger.warning(
            "Could not load default corpus from settings; falling back to %s",
            SUPPORT_KB_CORPUS,
        )
    return SUPPORT_KB_CORPUS


_IDENTIFIER_PATTERNS = (
    r"\b(INV-\d+)\b",
    r"\b(PO-\d+)\b",
    r"\b(RB-\d+)\b",
    r"\b(CUS-\d+)\b",
    r"\b(GD-\d+)\b",
)


def normalize_coderoad_environment(value: Any, original_message: str | None = None) -> str | None:
    """Return LIVE or TEST, or None when environment is missing or too vague."""
    candidates: list[str] = []
    if value is not None and str(value).strip():
        candidates.append(str(value).strip())
    if original_message:
        candidates.append(original_message)

    for raw in candidates:
        lower = raw.lower()
        if any(
            phrase in lower
            for phrase in (
                "specific environment",
                "certain environment",
                "particular environment",
                "a specific environment",
                "in a specific environment",
            )
        ):
            continue
        if re.search(r"\b(live|production floor|real production|in production)\b", lower):
            return "LIVE"
        if re.search(r"\b(test|staging|sandbox|uat)\b", lower):
            return "TEST"
        if lower in ("live", "production", "prod"):
            return "LIVE"
        if lower in ("test", "staging", "sandbox"):
            return "TEST"
    return None


def _infer_identifier_from_text(text: str) -> str | None:
    for pattern in _IDENTIFIER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def _infer_module_from_text(text: str) -> str | None:
    lower = text.lower()
    if any(word in lower for word in ("vat", "tax", "invoice", "billing", "ledger")):
        return "Billing"
    if any(word in lower for word in ("production order", "corrugator", "machine queue", "optimizer")):
        return "Production"
    if any(word in lower for word in ("dashboard", "kpi", "reporting")):
        return "Sales"
    if any(word in lower for word in ("shipment", "load guide", "logistics")):
        return "Logistics"
    return None


def user_query_suggests_display_issue(query: str | None) -> bool:
    if not query:
        return False
    lower = query.lower()
    display_terms = (
        "black screen",
        "blank screen",
        "white screen",
        "empty screen",
        "screen is",
        "screen totally",
        "totally black",
        "totally blank",
        "not loading",
        "dashboard",
        "panel",
        "queue screen",
    )
    return any(term in lower for term in display_terms)


class _IntakeToolContext:
    def __init__(self, corpus: str) -> None:
        self.state: dict[str, Any] = {"current_corpus": corpus}


def build_search_query(collected_fields: dict[str, Any], original_message: str | None) -> str:
    parts: list[str] = []
    if original_message:
        parts.append(original_message.strip())
    for key in (
        "summary",
        "system",
        "actual_behavior",
        "error_message",
        "expected_behavior",
        "environment",
    ):
        val = collected_fields.get(key)
        if val:
            text = str(val).strip()
            if text and text not in parts:
                parts.append(text)
    query = " ".join(parts) if parts else "support request"
    return _expand_search_query(query)


def _expand_search_query(query: str) -> str:
    """Add retrieval hints for common symptom phrasing gaps (e.g. black vs blank screen)."""
    if not user_query_suggests_display_issue(query):
        return query
    hints = [
        "blank screen",
        "black screen",
        "dashboard not loading",
        "KB-012",
        "browser cache",
        "machine queue blank",
    ]
    return f"{query} {' '.join(hints)}"


def search_knowledge_hub(
    collected_fields: dict[str, Any],
    original_message: str | None = None,
) -> tuple[list[KnowledgeResult], float]:
    corpus = get_intake_search_corpus()
    query = build_search_query(collected_fields, original_message)
    ctx = _IntakeToolContext(corpus)
    result = rag_query(corpus, query, ctx)

    if result.get("status") != "success":
        logger.info(
            "KB search in corpus %r returned no success: %s",
            corpus,
            result.get("message"),
        )
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

    logger.info(
        "KB search corpus=%r query=%r results=%d top_score=%.3f",
        corpus,
        query[:120],
        len(knowledge_results),
        top_score,
    )
    return knowledge_results, top_score


def meets_confidence_threshold(top_score: float, result_count: int) -> bool:
    global_cfg = get_global_config()
    threshold = float(
        global_cfg.get("knowledge_confidence_threshold", INTAKE_KB_CONFIDENCE_THRESHOLD)
    )
    min_results = int(global_cfg.get("knowledge_min_results", 1))
    return top_score >= threshold and result_count >= min_results


def is_actionable_kb_answer(answer: str) -> bool:
    """True when the grounded answer is substantive enough to offer the user."""
    text = (answer or "").strip()
    if len(text) < 40:
        return False
    lower = text.lower()
    if is_follow_up_collection_prompt(text):
        return False
    return not any(marker in lower for marker in _NO_ANSWER_MARKERS)


def is_follow_up_collection_prompt(answer: str) -> bool:
    """True when the model is asking the user for more details, not giving a fix."""
    lower = answer.lower()
    markers = (
        "could you please",
        "can you please",
        "please tell me",
        "please provide",
        "please include",
        "please share",
        "in your next message",
        "to help me understand",
        "to route this correctly",
        "once i have",
    )
    return any(m in lower for m in markers)


def _chunks_suggest_display_issue(results: list[KnowledgeResult]) -> bool:
    blob = " ".join(r.text.lower() for r in results[:5])
    markers = (
        "kb-012",
        "blank screen",
        "blank panel",
        "browser cache",
        "clear browsing data",
        "machine queue",
        "dashboard",
        "totally blank",
    )
    return any(m in blob for m in markers)


def _fallback_display_guidance(
    results: list[KnowledgeResult], query: str | None = None
) -> str | None:
    """Return KB-grounded steps when the LLM declines but retrieval clearly matches."""
    if not user_query_suggests_display_issue(query):
        return None
    if not _chunks_suggest_display_issue(results):
        return None

    for r in results:
        text = r.text
        lower = text.lower()
        if "clear browsing data" in lower or "kb-012" in lower or "cached images" in lower:
            source = r.source_name or "Knowledge Base"
            return (
                "A blank or black screen is often caused by a browser cache conflict. "
                "Try these steps:\n\n"
                "1. Press `Ctrl + Shift + Delete` (Windows) or `Cmd + Shift + Delete` (Mac) "
                "to open **Clear Browsing Data**.\n"
                "2. Select **Cached images and files** and **Cookies and other site data** "
                "for the **CoderoadERP domain only**.\n"
                "3. Set the time range to **Last 7 days** and click **Clear Data**.\n"
                "4. Close all CoderoadERP tabs, open a fresh tab, log in, and reopen your screen.\n"
                "5. If still blank, try a **Private / Incognito** window to confirm whether "
                "it's cache-related or server-side."
            )

    return None


def coderoad_missing_fields(
    collected_fields: dict[str, Any],
    original_message: str | None = None,
) -> list[str]:
    """CoderoadERP variables required before KB resolution or ticket creation."""
    mapped = dict(collected_fields)
    message = (original_message or "").strip()

    if not mapped.get("module") and mapped.get("system"):
        mapped["module"] = mapped["system"]
    if not mapped.get("module") and message:
        inferred_module = _infer_module_from_text(message)
        if inferred_module:
            mapped["module"] = inferred_module
    if not mapped.get("description"):
        mapped["description"] = (
            mapped.get("actual_behavior")
            or mapped.get("summary")
            or message
            or None
        )
    if not mapped.get("identifier"):
        for key in ("identifier", "document_id", "order_id", "batch_id"):
            if mapped.get(key):
                mapped["identifier"] = mapped[key]
                break
        if not mapped.get("identifier") and message:
            inferred_id = _infer_identifier_from_text(message)
            if inferred_id:
                mapped["identifier"] = inferred_id

    env = normalize_coderoad_environment(mapped.get("environment"), message)
    if env:
        mapped["environment"] = env
    else:
        mapped.pop("environment", None)

    required = ("module", "identifier", "description", "environment")
    return [field for field in required if not mapped.get(field)]


def has_complete_coderoad_context(
    collected_fields: dict[str, Any],
    original_message: str | None = None,
) -> bool:
    return not coderoad_missing_fields(collected_fields, original_message)


def get_coderoad_batch_follow_up(
    original_message: str | None,
    missing_fields: list[str],
    knowledge_results: list[KnowledgeResult],
) -> str | None:
    """CoderoadERP-style missing-info prompt aligned with indexed demo docs."""
    if get_intake_search_corpus() != "amtech-demo":
        return None

    understood = (original_message or "your issue").strip()
    if user_query_suggests_display_issue(understood) and _chunks_suggest_display_issue(
        knowledge_results
    ):
        return (
            f"Thank you for reaching out. I have registered **{understood}**.\n\n"
            "To route this correctly, please include **all** of the following in your "
            "next message:\n\n"
            "1. **Module** — which workspace or screen (e.g. Production Scheduler, Sales "
            "dashboard, Billing).\n"
            "2. **Document / Record ID** — line, machine, order, or batch code if known.\n"
            "3. **Environment** — LIVE (production) or TEST (staging).\n"
            "4. **Error code or footer patch version** — if any text appears on screen, even briefly.\n\n"
            "Once I have these, I can give self-service steps or open a priority ticket."
        )

    missing = missing_fields or coderoad_missing_fields(
        {"summary": understood}, original_message
    )
    if not missing:
        missing = ["module", "identifier", "description", "environment"]

    # Generic CoderoadERP variable collection
    field_prompts = {
        "module": "**Module** — affected workspace (Billing, Production, Sales, Inventory, CRM, IT/Admin).",
        "identifier": "**Document / Record ID** — invoice, PO, batch, customer, or line identifier.",
        "description": "**Description** — what you were doing, exact error or behavior.",
        "environment": "**Environment** — LIVE (production) or TEST (staging).",
        "system": "**Module / System** — CoderoadERP or CoderoadOPS module affected.",
        "actual_behavior": "**What is happening** — exact screen behavior or error message.",
        "business_impact": "**Business impact** — how operations are affected right now.",
    }
    lines = []
    for i, field in enumerate(missing, 1):
        prompt = field_prompts.get(field, f"**{format_field_label(field)}**")
        lines.append(f"{i}. {prompt}")

    if not lines:
        return None

    return (
        f"Thank you for reaching out. I have registered **{understood}**.\n\n"
        "I could not find a complete self-service answer yet. To resolve or escalate, "
        "please include **all** of the following in one message:\n\n"
        + "\n".join(lines)
    )


def _answer_from_kb_chunks(
    query: str,
    knowledge_results: list[KnowledgeResult],
) -> str | None:
    """Build a conversational answer from retrieval when chunks are strong enough."""
    if not knowledge_results:
        return None

    top = knowledge_results[0]
    if top.score < 0.55:
        return None

    blob = " ".join(r.text for r in knowledge_results[:3]).lower()
    combined = "\n\n".join(r.text.strip() for r in knowledge_results[:3] if r.text.strip())

    # Duplicate sequence / billing sequence guidance
    if "duplicate sequence" in blob or "sequence block" in blob:
        steps = re.findall(r"(?:^|\n)\s*(?:\d+[\).\]]\s+.+)", combined, re.MULTILINE)
        if steps:
            intro = (
                "A duplicate sequence block warning usually means the billing sequence "
                "counter is out of sync for that document type."
            )
            return intro + "\n\n" + "\n".join(step.strip() for step in steps[:6])

    # KB article with numbered steps
    numbered = re.findall(r"(?:^|\n)\s*(?:\d+[\).\]]\s+.+)", combined, re.MULTILINE)
    if len(numbered) >= 2:
        intro = "Based on our knowledge base, try the following:"
        return intro + "\n\n" + "\n".join(step.strip() for step in numbered[:8])

    kb_match = re.search(r"\bKB-\d+\b", combined, re.IGNORECASE)
    if kb_match and len(combined) > 120:
        excerpt = combined[:900].strip()
        return (
            f"This matches {kb_match.group(0).upper()}. "
            f"Here is the recommended guidance:\n\n{excerpt}"
        )

    if top.score >= 0.72 and len(top.text.strip()) > 160:
        return top.text.strip()[:1200]

    return None


def generate_grounded_answer(
    query: str,
    knowledge_results: list[KnowledgeResult],
) -> str:
    if not knowledge_results:
        return ""

    chunk_answer = _answer_from_kb_chunks(query, knowledge_results)
    if chunk_answer and is_actionable_kb_answer(chunk_answer):
        logger.info("Using chunk-based KB answer (no Gemini call)")
        return chunk_answer

    context_chunks = []
    for i, r in enumerate(knowledge_results[:5], 1):
        context_chunks.append(
            f"[Source {i}: {r.source_name}]\n{r.text}\n"
        )
    context = "\n---\n".join(context_chunks)

    prompt = f"""You are the CoderoadERP AI Support Copilot.
Answer using ONLY the retrieved knowledge below, in a warm conversational tone.

Rules:
- Do not mention file names, document titles, or "Sources" in your reply.
- You may reference KB article IDs naturally (e.g. "this matches KB-012") when helpful.
- Treat "black screen", "blank screen", "white screen", and "not loading" as display/render issues.
- If content matches KB-012 (browser cache / dashboard blank), provide those numbered steps.
- If the user gave little context, still share the best-matching self-service steps from retrieval when present.
- Only say you could not find a definitive answer when retrieval truly does not cover the symptom.
- Keep the response concise and speak directly to the user.

User question / context: {query}

Retrieved content:
{context}

Provide a concise, conversational answer with resolution steps when available.
"""
    return generate_content(
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
