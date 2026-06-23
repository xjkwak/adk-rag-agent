"""REST API for Knowledge HUB configuration (documents, agent settings)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import settings_store
from .config import USE_LOCAL_RAG
from .amtech_instruction import AMTECH_INSTRUCTION
from .tools.get_corpus_info import get_corpus_info
from .tools.utils import check_corpus_exists

logger = logging.getLogger(__name__)

router = APIRouter()


class _AdminToolContext:
    def __init__(self) -> None:
        self.state: dict[str, Any] = {}


class AgentConfigResponse(BaseModel):
    model: str
    instruction: str
    default_instruction: str
    available_models: list[str]
    default_corpus: str


class AgentConfigUpdate(BaseModel):
    model: str | None = None
    instruction: str | None = None
    default_corpus: str | None = None


class CorpusListResponse(BaseModel):
    corpora: list[dict[str, Any]]
    default_corpus: str


class DocumentListResponse(BaseModel):
    corpus_name: str
    corpus_display_name: str
    file_count: int
    files: list[dict[str, Any]]


class UploadResponse(BaseModel):
    status: str
    message: str
    files_added: int = 0
    paths: list[str] = Field(default_factory=list)
    invalid_paths: list[str] = Field(default_factory=list)


class CorpusCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class CorpusMutationResponse(BaseModel):
    status: str
    message: str
    corpus_name: str
    display_name: str | None = None
    corpus_created: bool | None = None


def _apply_agent_runtime() -> None:
    """Reload live agent model/instruction from persisted settings."""
    try:
        from . import agent as agent_module

        runtime = settings_store.get_agent_settings()
        agent_module.root_agent.model = runtime["model"]
        agent_module.root_agent.instruction = runtime["instruction"]
    except Exception as e:
        logger.warning("Could not patch live agent: %s", e)


@router.get("/agent", response_model=AgentConfigResponse)
def get_agent_config() -> AgentConfigResponse:
    settings = settings_store.load_settings()
    return AgentConfigResponse(
        model=settings["model"],
        instruction=settings["instruction"],
        default_instruction=AMTECH_INSTRUCTION.strip(),
        available_models=settings_store.get_available_gemini_models(
            include=settings["model"]
        ),
        default_corpus=settings["default_corpus"],
    )


@router.put("/agent", response_model=AgentConfigResponse)
def update_agent_config(body: AgentConfigUpdate) -> AgentConfigResponse:
    if body.model is None and body.instruction is None and body.default_corpus is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        saved = settings_store.save_settings(
            model=body.model,
            instruction=body.instruction,
            default_corpus=body.default_corpus,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    _apply_agent_runtime()
    return get_agent_config()


@router.post("/agent/reset", response_model=AgentConfigResponse)
def reset_agent_config() -> AgentConfigResponse:
    settings_store.reset_agent_settings()
    _apply_agent_runtime()
    return get_agent_config()


@router.get("/corpora", response_model=CorpusListResponse)
def list_corpora() -> CorpusListResponse:
    settings = settings_store.load_settings()
    if USE_LOCAL_RAG:
        from .local_rag import store as local_store

        result = local_store.list_corpora_dict()
        corpora = result.get("corpora", [])
    else:
        from .tools.list_corpora import list_corpora as list_corpora_tool

        result = list_corpora_tool()
        corpora = result.get("corpora", [])

    return CorpusListResponse(
        corpora=corpora,
        default_corpus=settings["default_corpus"],
    )


@router.post("/corpora", response_model=CorpusMutationResponse)
def create_corpus_endpoint(body: CorpusCreateRequest) -> CorpusMutationResponse:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Corpus name is required")

    ctx = _AdminToolContext()
    from .tools.create_corpus import create_corpus

    result = create_corpus(name, ctx)
    status = result.get("status", "error")
    if status == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to create corpus"))

    display = result.get("display_name") or name
    return CorpusMutationResponse(
        status=status,
        message=result.get("message", ""),
        corpus_name=result.get("corpus_name", name),
        display_name=display,
        corpus_created=result.get("corpus_created"),
    )


@router.delete("/corpora/{corpus_name}", response_model=CorpusMutationResponse)
def delete_corpus_endpoint(corpus_name: str) -> CorpusMutationResponse:
    ctx = _AdminToolContext()
    if not check_corpus_exists(corpus_name, ctx):
        raise HTTPException(status_code=404, detail=f"Corpus '{corpus_name}' not found")

    from .tools.delete_corpus import delete_corpus

    result = delete_corpus(corpus_name, confirm=True, tool_context=ctx)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Delete failed"))

    settings = settings_store.load_settings()
    if settings["default_corpus"] == corpus_name:
        if USE_LOCAL_RAG:
            from .local_rag import store as local_store

            listed = local_store.list_corpora_dict().get("corpora", [])
        else:
            from .tools.list_corpora import list_corpora as list_corpora_tool

            listed = list_corpora_tool().get("corpora", [])
        names = [c.get("display_name", "") for c in listed if c.get("display_name")]
        fallback = names[0] if names else settings_store.get_default_corpus()
        settings_store.save_settings(default_corpus=fallback)
    _apply_agent_runtime()

    return CorpusMutationResponse(
        status="success",
        message=result.get("message", f"Deleted corpus '{corpus_name}'"),
        corpus_name=corpus_name,
        display_name=corpus_name,
    )


@router.get("/corpora/{corpus_name}/documents", response_model=DocumentListResponse)
def list_documents(corpus_name: str) -> DocumentListResponse:
    ctx = _AdminToolContext()
    if not check_corpus_exists(corpus_name, ctx):
        raise HTTPException(status_code=404, detail=f"Corpus '{corpus_name}' not found")

    info = get_corpus_info(corpus_name, ctx)
    if info.get("status") == "error":
        raise HTTPException(status_code=500, detail=info.get("message", "Failed to list documents"))

    return DocumentListResponse(
        corpus_name=corpus_name,
        corpus_display_name=info.get("corpus_display_name", corpus_name),
        file_count=info.get("file_count", 0),
        files=info.get("files", []),
    )


@router.post("/corpora/{corpus_name}/documents", response_model=UploadResponse)
async def upload_documents(
    corpus_name: str,
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    ctx = _AdminToolContext()
    if not check_corpus_exists(corpus_name, ctx):
        from .tools.create_corpus import create_corpus

        created = create_corpus(corpus_name, ctx)
        if created.get("status") not in ("success", "info"):
            raise HTTPException(
                status_code=400,
                detail=created.get("message", "Failed to create corpus"),
            )

    saved_paths: list[str] = []
    with tempfile.TemporaryDirectory(prefix="kh_upload_") as tmpdir:
        tmp = Path(tmpdir)
        for upload in files:
            if not upload.filename:
                continue
            safe_name = Path(upload.filename).name
            dest = tmp / safe_name
            content = await upload.read()
            dest.write_bytes(content)
            saved_paths.append(str(dest.resolve()))

        if not saved_paths:
            raise HTTPException(status_code=400, detail="No valid files received")

        from .tools.add_data import add_data

        result = add_data(corpus_name, saved_paths, ctx)

    status = result.get("status", "error")
    if status == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Upload failed"))

    return UploadResponse(
        status=status,
        message=result.get("message", ""),
        files_added=int(result.get("files_added", 0)),
        paths=result.get("paths", saved_paths),
        invalid_paths=result.get("invalid_paths", []),
    )


@router.delete("/corpora/{corpus_name}/documents/{document_id}")
def delete_document(corpus_name: str, document_id: str) -> dict[str, Any]:
    ctx = _AdminToolContext()
    if not check_corpus_exists(corpus_name, ctx):
        raise HTTPException(status_code=404, detail=f"Corpus '{corpus_name}' not found")

    from .tools.delete_document import delete_document as delete_document_tool

    result = delete_document_tool(corpus_name, document_id, ctx)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Delete failed"))
    return result
