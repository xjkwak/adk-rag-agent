"""Support intake conversation orchestrator — controlled state machine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..config import get_jira_settings
from ..adapters.jira_mcp import (
    build_ticket_preview,
    create_jira_issue,
    extract_issue_key,
    is_fixed_issue_mode,
)
from ..adapters.knowledge_hub import (
    coderoad_missing_fields,
    generate_grounded_answer,
    get_coderoad_batch_follow_up,
    get_intake_search_corpus,
    has_complete_coderoad_context,
    is_actionable_kb_answer,
    normalize_coderoad_environment,
    search_knowledge_hub,
    _fallback_display_guidance,
)
from ..config_loader import (
    get_batch_follow_up_message,
    get_global_config,
    get_optional_fields,
    get_required_fields,
    load_intake_config,
)
from . import nlu
from .state import ConversationState, ConversationStatus, TicketPreview

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResponse:
    assistant_message: str
    state: ConversationState
    ui_hints: dict[str, Any]
    kb_answer: str | None = None
    articles: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "assistantMessage": self.assistant_message,
            "state": self.state.to_dict(),
            "uiHints": self.ui_hints,
            "kbAnswer": self.kb_answer,
            "articles": self.articles,
        }


def _ui_hints(state: ConversationState) -> dict[str, Any]:
    return {
        "showTicketPreview": state.ticket_preview is not None
        and state.status == ConversationStatus.AWAITING_TICKET_CONFIRMATION,
        "showKbArticles": False,
        "awaitingConfirmation": state.status == ConversationStatus.AWAITING_TICKET_CONFIRMATION,
        "awaitingSolutionConfirmation": state.status == ConversationStatus.VERIFYING_SOLUTION,
        "showJiraCreated": state.jira_issue_key is not None,
        "isComplete": state.status in (ConversationStatus.COMPLETE, ConversationStatus.CLOSED),
    }


def _articles_from_state(state: ConversationState) -> list[dict[str, Any]]:
    return [
        {
            "sourceName": r.source_name,
            "sourceUri": r.source_uri,
            "score": r.score,
            "excerpt": r.text[:300],
        }
        for r in state.knowledge_results[:5]
    ]


def _merge_fields(state: ConversationState, request_type: str) -> None:
    required = get_required_fields(request_type)
    optional = get_optional_fields(request_type)
    all_fields = required + [f for f in optional if f not in required]
    if get_intake_search_corpus() == "amtech-demo":
        for field in ("module", "identifier", "description", "environment"):
            if field not in all_fields:
                all_fields.append(field)
    extracted = nlu.extract_fields(
        state.messages, request_type, all_fields, state.collected_fields
    )
    for k, v in extracted.items():
        if v is not None:
            state.collected_fields[k] = v
    if get_intake_search_corpus() == "amtech-demo":
        if state.collected_fields.get("system") and not state.collected_fields.get("module"):
            state.collected_fields["module"] = state.collected_fields["system"]
        if state.collected_fields.get("actual_behavior") and not state.collected_fields.get(
            "description"
        ):
            state.collected_fields["description"] = state.collected_fields["actual_behavior"]
        env = normalize_coderoad_environment(
            state.collected_fields.get("environment"), state.original_message
        )
        if env:
            state.collected_fields["environment"] = env
        elif "environment" in state.collected_fields:
            del state.collected_fields["environment"]
    else:
        state.compute_missing_fields(required)


def _sync_ticket_collection_gaps(state: ConversationState, request_type: str) -> None:
    """Ensure required ticket fields are collected before showing a Jira preview."""
    if get_intake_search_corpus() == "amtech-demo":
        gaps = coderoad_missing_fields(state.collected_fields, state.original_message)
        state.missing_fields = gaps
        return
    required = get_required_fields(request_type)
    state.compute_missing_fields(required)


def _batch_follow_up(state: ConversationState) -> str | None:
    """Return a single message asking for all missing required fields."""
    global_cfg = get_global_config()
    max_rounds = int(global_cfg.get("max_follow_up_questions", 3))
    if state.follow_up_count >= max_rounds:
        return None
    if not state.missing_fields:
        return None

    coderoad_msg = get_coderoad_batch_follow_up(
        state.original_message,
        state.missing_fields,
        state.knowledge_results,
    )
    if coderoad_msg:
        footer = global_cfg.get(
            "batch_fields_footer",
            "You can reply in a single message with all of the information above.",
        )
        return f"{coderoad_msg}\n\n{footer}"

    return get_batch_follow_up_message(
        state.request_type or "unclear", state.missing_fields
    )


def _try_kb_resolution(state: ConversationState) -> OrchestratorResponse | None:
    """Search configured Knowledge Hub corpus and return an answer when retrieval supports one."""
    if get_intake_search_corpus() == "amtech-demo" and not has_complete_coderoad_context(
        state.collected_fields, state.original_message
    ):
        return None

    state.status = ConversationStatus.SEARCHING_KNOWLEDGE
    results, top_score = search_knowledge_hub(
        state.collected_fields, state.original_message
    )
    state.knowledge_results = results
    state.kb_confidence = top_score

    if not results:
        return None

    query = state.original_message or state.collected_fields.get("summary") or ""
    answer = generate_grounded_answer(query, results)
    if not is_actionable_kb_answer(answer):
        fallback = _fallback_display_guidance(results, query)
        if fallback:
            logger.info(
                "Using KB fallback guidance for display issue (top_score=%.3f)",
                top_score,
            )
            answer = fallback
        else:
            logger.info(
                "KB retrieval did not yield an actionable answer (top_score=%.3f)",
                top_score,
            )
            return None

    state.kb_answer = answer
    state.resolution_attempted = True
    state.status = ConversationStatus.VERIFYING_SOLUTION
    msg = f"{answer}\n\nDid this resolve your issue? (yes/no)"
    state.add_message("assistant", msg)
    return OrchestratorResponse(
        assistant_message=msg,
        state=state,
        ui_hints=_ui_hints(state),
        kb_answer=answer,
        articles=None,
    )


def _ask_missing_fields(state: ConversationState) -> OrchestratorResponse | None:
    msg = _batch_follow_up(state)
    if not msg:
        return None
    state.status = ConversationStatus.COLLECTING_INFORMATION
    state.follow_up_count += 1
    state.add_message("assistant", msg)
    return OrchestratorResponse(
        assistant_message=msg,
        state=state,
        ui_hints=_ui_hints(state),
    )


def _prepare_ticket(state: ConversationState) -> OrchestratorResponse:
    request_type = state.request_type or "unclear"
    description = nlu.generate_conversation_summary(
        state.collected_fields,
        request_type,
        state.messages,
        [r.to_dict() for r in state.knowledge_results],
    )
    preview = build_ticket_preview(
        state.collected_fields, request_type, description
    )
    state.ticket_preview = preview
    state.status = ConversationStatus.AWAITING_TICKET_CONFIRMATION

    ticket_action = "update" if is_fixed_issue_mode() else "create"
    fixed_key = str(get_jira_settings().get("fixed_issue_key", "")).strip()
    target_line = ""
    if fixed_key:
        target_line = (
            f"\n\nThis demo will **update** existing ticket **{fixed_key}** in Jira."
        )

    msg = (
        f"I have everything I need to open your support ticket. Please confirm the details "
        f"below or let me know if you'd like to change anything.{target_line}\n\n"
        f"**Summary:** {preview.summary}\n\n"
        f"**Type:** {preview.issue_type}\n\n"
        f"**Description preview:**\n{preview.description[:500]}"
        + ("..." if len(preview.description) > 500 else "")
        + f"\n\nReply **yes** to {ticket_action} the ticket, or **no** to revise."
    )
    return OrchestratorResponse(
        assistant_message=msg,
        state=state,
        ui_hints=_ui_hints(state),
        articles=_articles_from_state(state) if state.knowledge_results else None,
    )


def _begin_new_topic(state: ConversationState, user_message: str) -> None:
    """Allow follow-up questions in the same session after ticket creation or KB closure."""
    state.status = ConversationStatus.COLLECTING_INFORMATION
    state.request_type = None
    state.original_message = user_message
    state.collected_fields = {}
    state.missing_fields = []
    state.follow_up_count = 0
    state.ticket_preview = None
    state.ticket_confirmed = False
    state.kb_answer = None
    state.knowledge_results = []
    state.kb_confidence = 0.0
    state.resolution_attempted = False
    state.solution_accepted = None


async def process_message(
    state: ConversationState,
    user_message: str,
) -> OrchestratorResponse:
    state.add_message("user", user_message)

    if state.status == ConversationStatus.VERIFYING_SOLUTION:
        feedback = nlu.detect_solution_feedback(user_message)
        if feedback is True:
            state.solution_accepted = True
            state.status = ConversationStatus.CLOSED
            return OrchestratorResponse(
                assistant_message=(
                    "Great! I'm glad that resolved your issue. "
                    "No ticket was created. Feel free to reach out if you need anything else."
                ),
                state=state,
                ui_hints=_ui_hints(state),
                kb_answer=state.kb_answer,
                articles=_articles_from_state(state),
            )
        if feedback is False:
            state.solution_accepted = False
            state.status = ConversationStatus.COLLECTING_INFORMATION
            _sync_ticket_collection_gaps(state, state.request_type or "unclear")
            if state.missing_fields:
                batch = _ask_missing_fields(state)
                if batch:
                    return batch
            return _prepare_ticket(state)

    if state.status == ConversationStatus.AWAITING_TICKET_CONFIRMATION:
        confirm = nlu.detect_ticket_confirmation(user_message)
        if confirm is True:
            return await confirm_ticket(state)
        if confirm is False:
            state.status = ConversationStatus.COLLECTING_INFORMATION
            msg = "What would you like to change? Please provide the updated information."
            state.add_message("assistant", msg)
            return OrchestratorResponse(
                assistant_message=msg,
                state=state,
                ui_hints=_ui_hints(state),
            )

    if state.status in (ConversationStatus.COMPLETE, ConversationStatus.CLOSED):
        _begin_new_topic(state, user_message)

    if state.original_message is None:
        state.original_message = user_message

    if state.request_type is None:
        state.request_type = nlu.classify_request(state.messages)
        logger.info("Classified request as %s", state.request_type)

    request_type = state.request_type

    _merge_fields(state, request_type)

    # 1. Collect missing CoderoadERP context before KB or ticket (e.g. LIVE vs TEST)
    _sync_ticket_collection_gaps(state, request_type)
    if state.missing_fields:
        batch = _ask_missing_fields(state)
        if batch:
            return batch

    # 2. Try Knowledge Hub when all critical variables are present
    kb_response = _try_kb_resolution(state)
    if kb_response:
        return kb_response

    # 3. All required fields present — ticket preview
    return _prepare_ticket(state)


async def confirm_ticket(state: ConversationState) -> OrchestratorResponse:
    if not state.ticket_preview:
        state.ticket_preview = build_ticket_preview(
            state.collected_fields,
            state.request_type or "unclear",
            nlu.generate_conversation_summary(
                state.collected_fields,
                state.request_type or "unclear",
                state.messages,
                [r.to_dict() for r in state.knowledge_results],
            ),
        )

    state.status = ConversationStatus.CREATING_TICKET
    fixed_key = str(get_jira_settings().get("fixed_issue_key", "")).strip()
    try:
        result = await create_jira_issue(state.ticket_preview)
        key, url = extract_issue_key(result)
        if fixed_key and not key:
            key = fixed_key
            url = url or f"{get_jira_settings()['url'].rstrip('/')}/browse/{fixed_key}"
        state.jira_issue_key = key
        state.jira_issue_url = url
        state.ticket_confirmed = True
        state.status = ConversationStatus.COMPLETE
        verb = "updated" if fixed_key else "created"
        msg = (
            f"Your support ticket **{key}** has been {verb}.\n\n"
            f"[View in Jira]({url})\n\n"
            "Our team will review your request. Thank you!\n\n"
            "If you have another question, just type it below."
        )
    except Exception as exc:
        logger.exception("Failed to submit Jira issue")
        state.status = ConversationStatus.AWAITING_TICKET_CONFIRMATION
        verb = "update" if is_fixed_issue_mode() else "create"
        msg = (
            f"I couldn't {verb} the Jira ticket: {exc}\n\n"
            "Please check Jira configuration and try again, or contact support directly."
        )

    state.add_message("assistant", msg)
    return OrchestratorResponse(
        assistant_message=msg,
        state=state,
        ui_hints=_ui_hints(state),
        articles=_articles_from_state(state) if state.knowledge_results else None,
    )


def create_opening_message() -> str:
    cfg = load_intake_config()
    return cfg.get("global", {}).get("opening_message", "How can I help you today?")
