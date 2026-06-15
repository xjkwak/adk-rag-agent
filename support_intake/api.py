"""FastAPI routes for Support Intake Assistant."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .adapters.speech import ALLOWED_MIME_TYPES, transcribe_audio
from .orchestrator.machine import (
    OrchestratorResponse,
    confirm_ticket,
    create_opening_message,
    process_message,
)
from .orchestrator.session_store import session_store
from .orchestrator.state import ConversationState, ConversationStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class SessionResponse(BaseModel):
    conversation_id: str
    assistant_message: str
    state: dict[str, Any]


class MessageRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    assistant_message: str
    state: dict[str, Any]
    ui_hints: dict[str, Any]
    kb_answer: str | None = None
    articles: list[dict[str, Any]] | None = None


class ConfirmTicketRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    confirmed: bool = True


class TranscribeResponse(BaseModel):
    transcript: str
    mime_type: str


def _response_from_orchestrator(resp: OrchestratorResponse) -> MessageResponse:
    return MessageResponse(
        assistant_message=resp.assistant_message,
        state=resp.state.to_dict(),
        ui_hints=resp.ui_hints,
        kb_answer=resp.kb_answer,
        articles=resp.articles,
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    state = session_store.create()
    opening = create_opening_message()
    state.status = ConversationStatus.COLLECTING_INFORMATION
    state.add_message("assistant", opening)
    session_store.save(state)
    return SessionResponse(
        conversation_id=state.conversation_id,
        assistant_message=opening,
        state=state.to_dict(),
    )


@router.get("/sessions/{conversation_id}")
async def get_session(conversation_id: str) -> dict[str, Any]:
    state = session_store.get(conversation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return state.to_dict()


@router.post("/message", response_model=MessageResponse)
async def post_message(body: MessageRequest) -> MessageResponse:
    state = session_store.get(body.conversation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        resp = await process_message(state, body.message.strip())
        session_store.save(resp.state)
        return _response_from_orchestrator(resp)
    except Exception as exc:
        logger.exception("Error processing intake message")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/confirm-ticket", response_model=MessageResponse)
async def post_confirm_ticket(body: ConfirmTicketRequest) -> MessageResponse:
    state = session_store.get(body.conversation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not body.confirmed:
        state.status = ConversationStatus.COLLECTING_INFORMATION
        msg = "Ticket creation cancelled. What would you like to update?"
        state.add_message("assistant", msg)
        session_store.save(state)
        return MessageResponse(
            assistant_message=msg,
            state=state.to_dict(),
            ui_hints={"awaitingConfirmation": False},
        )
    try:
        resp = await confirm_ticket(state)
        session_store.save(resp.state)
        return _response_from_orchestrator(resp)
    except Exception as exc:
        logger.exception("Error confirming ticket")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/transcribe", response_model=TranscribeResponse)
async def post_transcribe(
    file: UploadFile = File(...),
) -> TranscribeResponse:
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {file.content_type}. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")
    try:
        transcript = transcribe_audio(data, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TranscribeResponse(transcript=transcript, mime_type=file.content_type)
