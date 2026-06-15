"""Conversation state models for the support intake workflow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class ConversationStatus(str, Enum):
    START = "start"
    COLLECTING_INFORMATION = "collecting_information"
    SEARCHING_KNOWLEDGE = "searching_knowledge"
    PROVIDING_SOLUTION = "providing_solution"
    VERIFYING_SOLUTION = "verifying_solution"
    PREPARING_TICKET = "preparing_ticket"
    AWAITING_TICKET_CONFIRMATION = "awaiting_ticket_confirmation"
    CREATING_TICKET = "creating_ticket"
    COMPLETE = "complete"
    CLOSED = "closed"


@dataclass
class KnowledgeResult:
    source_name: str
    source_uri: str
    text: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TicketPreview:
    summary: str
    description: str
    issue_type: str
    request_type: str
    priority: str | None = None
    environment: str | None = None
    labels: list[str] = field(default_factory=list)
    additional_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationState:
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ConversationStatus = ConversationStatus.START
    request_type: str | None = None
    original_message: str | None = None
    transcript: str | None = None
    collected_fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    follow_up_count: int = 0
    messages: list[dict[str, str]] = field(default_factory=list)
    knowledge_results: list[KnowledgeResult] = field(default_factory=list)
    kb_answer: str | None = None
    kb_confidence: float = 0.0
    resolution_attempted: bool = False
    solution_accepted: bool | None = None
    ticket_preview: TicketPreview | None = None
    ticket_confirmed: bool = False
    jira_issue_key: str | None = None
    jira_issue_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversationId": self.conversation_id,
            "status": self.status.value,
            "requestType": self.request_type,
            "originalMessage": self.original_message,
            "transcript": self.transcript,
            "collectedFields": self.collected_fields,
            "missingFields": self.missing_fields,
            "followUpCount": self.follow_up_count,
            "knowledgeResults": [r.to_dict() for r in self.knowledge_results],
            "kbAnswer": self.kb_answer,
            "kbConfidence": self.kb_confidence,
            "resolutionAttempted": self.resolution_attempted,
            "solutionAccepted": self.solution_accepted,
            "ticketPreview": self.ticket_preview.to_dict() if self.ticket_preview else None,
            "ticketConfirmed": self.ticket_confirmed,
            "jiraIssueKey": self.jira_issue_key,
            "jiraIssueUrl": self.jira_issue_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationState:
        state = cls(
            conversation_id=data.get("conversationId", str(uuid.uuid4())),
            status=ConversationStatus(data.get("status", "start")),
            request_type=data.get("requestType"),
            original_message=data.get("originalMessage"),
            transcript=data.get("transcript"),
            collected_fields=dict(data.get("collectedFields", {})),
            missing_fields=list(data.get("missingFields", [])),
            follow_up_count=int(data.get("followUpCount", 0)),
            kb_answer=data.get("kbAnswer"),
            kb_confidence=float(data.get("kbConfidence", 0.0)),
            resolution_attempted=bool(data.get("resolutionAttempted", False)),
            solution_accepted=data.get("solutionAccepted"),
            ticket_confirmed=bool(data.get("ticketConfirmed", False)),
            jira_issue_key=data.get("jiraIssueKey"),
            jira_issue_url=data.get("jiraIssueUrl"),
        )
        for r in data.get("knowledgeResults", []):
            state.knowledge_results.append(
                KnowledgeResult(
                    source_name=r.get("source_name", ""),
                    source_uri=r.get("source_uri", ""),
                    text=r.get("text", ""),
                    score=float(r.get("score", 0.0)),
                )
            )
        tp = data.get("ticketPreview")
        if tp:
            state.ticket_preview = TicketPreview(
                summary=tp.get("summary", ""),
                description=tp.get("description", ""),
                issue_type=tp.get("issue_type", "Task"),
                request_type=tp.get("request_type", ""),
                priority=tp.get("priority"),
                environment=tp.get("environment"),
                labels=list(tp.get("labels", [])),
                additional_info=dict(tp.get("additional_info", {})),
            )
        return state

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def compute_missing_fields(self, required: list[str]) -> list[str]:
        missing = []
        for f in required:
            val = self.collected_fields.get(f)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(f)
        self.missing_fields = missing
        return missing
