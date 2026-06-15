"""In-memory session store for intake conversations."""

from __future__ import annotations

import threading
from typing import Any

from .state import ConversationState


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self) -> ConversationState:
        state = ConversationState()
        with self._lock:
            self._sessions[state.conversation_id] = state.to_dict()
        return state

    def get(self, conversation_id: str) -> ConversationState | None:
        with self._lock:
            data = self._sessions.get(conversation_id)
        if data is None:
            return None
        return ConversationState.from_dict(data)

    def save(self, state: ConversationState) -> None:
        with self._lock:
            self._sessions[state.conversation_id] = state.to_dict()

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            self._sessions.pop(conversation_id, None)


session_store = SessionStore()
