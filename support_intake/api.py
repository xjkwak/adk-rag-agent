"""FastAPI routes for Support Intake Assistant."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .genai_utils import IntakeServiceError
from .adapters.attachments import process_attachments
from .adapters.speech import ALLOWED_MIME_TYPES, transcribe_audio
from .orchestrator.multi_input import UserMultiInput, compose_user_message
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

from .eval_api import router as eval_router

router.include_router(eval_router)


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


async def _handle_process_message(
    state: ConversationState,
    user_message: str,
    message_metadata: dict[str, Any] | None = None,
) -> MessageResponse:
    try:
        resp = await process_message(
            state,
            user_message,
            message_metadata=message_metadata,
        )
        session_store.save(resp.state)
        return _response_from_orchestrator(resp)
    except IntakeServiceError as exc:
        logger.warning("Intake AI service error: %s", exc)
        msg = exc.user_message
        state.add_message("assistant", msg)
        session_store.save(state)
        return MessageResponse(
            assistant_message=msg,
            state=state.to_dict(),
            ui_hints={
                "showTicketPreview": False,
                "showKbArticles": False,
                "awaitingConfirmation": False,
                "awaitingSolutionConfirmation": False,
                "showJiraCreated": False,
                "isComplete": False,
            },
        )
    except Exception as exc:
        logger.exception("Error processing intake message")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/message", response_model=MessageResponse)
async def post_message(body: MessageRequest) -> MessageResponse:
    state = session_store.get(body.conversation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await _handle_process_message(state, body.message.strip())


@router.post("/message/multi", response_model=MessageResponse)
async def post_message_multi(
    conversation_id: str = Form(...),
    message: str = Form(""),
    audio: UploadFile | None = File(None),
    attachments: list[UploadFile] | None = File(default=None),
) -> MessageResponse:
    """Accept text, optional audio, and optional file attachments in one request."""
    state = session_store.get(conversation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    text = message.strip()
    transcript: str | None = None

    if audio and audio.filename:
        if not audio.content_type or audio.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported audio type: {audio.content_type}. "
                    f"Allowed: {sorted(ALLOWED_MIME_TYPES)}"
                ),
            )
        audio_data = await audio.read()
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio file")
        try:
            transcript = transcribe_audio(audio_data, audio.content_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    attachment_files: list[tuple[str, bytes, str | None]] = []
    for upload in attachments or []:
        if not upload.filename:
            continue
        data = await upload.read()
        if not data:
            continue
        attachment_files.append(
            (upload.filename, data, upload.content_type),
        )

    processed_attachments: list = []
    if attachment_files:
        try:
            processed_attachments = process_attachments(attachment_files)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    user_input = UserMultiInput(
        text=text or None,
        transcript=transcript,
        attachments=processed_attachments,
    )
    if not user_input.has_content:
        raise HTTPException(
            status_code=400,
            detail="Provide a message, audio recording, or at least one attachment.",
        )

    composed, metadata = compose_user_message(user_input)
    if transcript:
        metadata["transcript"] = transcript

    return await _handle_process_message(state, composed, message_metadata=metadata)


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
    except IntakeServiceError as exc:
        logger.warning("Intake AI service error on ticket confirm: %s", exc)
        msg = exc.user_message
        state.add_message("assistant", msg)
        session_store.save(state)
        return MessageResponse(
            assistant_message=msg,
            state=state.to_dict(),
            ui_hints={"awaitingConfirmation": True},
        )
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
