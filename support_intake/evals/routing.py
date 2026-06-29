"""Map orchestrator state to Testing Framework route outcomes."""

from __future__ import annotations

from ..orchestrator.machine import OrchestratorResponse
from ..orchestrator.state import ConversationState, ConversationStatus


def derive_route_outcome(
    state: ConversationState,
    response: OrchestratorResponse,
) -> str:
    if (
        state.status == ConversationStatus.VERIFYING_SOLUTION
        and response.kb_answer
    ):
        return "route_a"
    if state.status == ConversationStatus.AWAITING_TICKET_CONFIRMATION:
        return "route_b"
    if (
        state.status == ConversationStatus.COLLECTING_INFORMATION
        and state.missing_fields
    ):
        return "ask_missing"
    return "unknown"
