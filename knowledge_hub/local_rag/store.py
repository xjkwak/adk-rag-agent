"""
Local RAG persistence: registry + ChromaDB per corpus.

Resource names mirror Vertex shape so existing tool contracts stay compatible:
  projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_uuid}
"""

from __future__ import annotations

import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

import chromadb
import httpx
from google.adk.tools.tool_context import ToolContext
from pypdf import PdfReader

logger = logging.getLogger(__name__)

_lock = RLock()


def _cfg():
    from .. import config

    return config


def _base_dir() -> Path:
    cfg = _cfg()
    p = Path(cfg.LOCAL_RAG_DATA_DIR).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    (p / "chromadb").mkdir(parents=True, exist_ok=True)
    return p


def _registry_path() -> Path:
    return _base_dir() / "corpora_registry.json"


def _load_registry() -> dict[str, Any]:
    with _lock:
        path = _registry_path()
        if not path.exists():
            return {"corpora": []}
        return json.loads(path.read_text(encoding="utf-8"))


def _save_registry(data: dict[str, Any]) -> None:
    with _lock:
        _registry_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _resource_name(corpus_id: str) -> str:
    cfg = _cfg()
    pid = cfg.PROJECT_ID or "local"
    loc = cfg.LOCATION or "local"
    return f"projects/{pid}/locations/{loc}/ragCorpora/{corpus_id}"


def _collection_name(corpus_id: str) -> str:
    # Chroma collection names: alphanumeric + underscore; keep stable per corpus id
    return f"kh_{corpus_id.replace('-', '_')}"


def _client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(_base_dir() / "chromadb"))


def _find_corpus_entry(registry: dict[str, Any], *, corpus_id: str | None = None, display_name: str | None = None, resource_name: str | None = None) -> dict[str, Any] | None:
    for c in registry.get("corpora", []):
        if corpus_id and c.get("corpus_id") == corpus_id:
            return c
        if display_name and c.get("display_name") == display_name:
            return c
        if resource_name and c.get("resource_name") == resource_name:
            return c
        if resource_name and _resource_name(c["corpus_id"]) == resource_name:
            return c
    return None


def resolve_corpus_resource_name(corpus_name: str) -> str:
    """Resolve display name, partial id, or full resource name to canonical resource name."""
    if re.match(r"^projects/[^/]+/locations/[^/]+/ragCorpora/[^/]+$", corpus_name):
        return corpus_name

    registry = _load_registry()
    entry = _find_corpus_entry(registry, display_name=corpus_name)
    if entry:
        return entry["resource_name"]

    tail = corpus_name.split("/")[-1] if "/" in corpus_name else corpus_name
    entry = _find_corpus_entry(registry, corpus_id=tail)
    if entry:
        return entry["resource_name"]

    # New corpus id path (not yet in registry) — keep Vertex-style construction
    cfg = _cfg()
    corpus_id = re.sub(r"[^a-zA-Z0-9_-]", "_", tail)
    return f"projects/{cfg.PROJECT_ID or 'local'}/locations/{cfg.LOCATION or 'local'}/ragCorpora/{corpus_id}"


def corpus_exists(corpus_name: str, tool_context: ToolContext) -> bool:
    if tool_context.state.get(f"corpus_exists_{corpus_name}"):
        return True

    registry = _load_registry()
    for c in registry.get("corpora", []):
        if (
            c.get("resource_name") == corpus_name
            or c.get("display_name") == corpus_name
            or c.get("corpus_id") == corpus_name.split("/")[-1]
        ):
            tool_context.state[f"corpus_exists_{corpus_name}"] = True
            tool_context.state[f"corpus_exists_{c['resource_name']}"] = True
            tool_context.state[f"corpus_exists_{c['display_name']}"] = True
            if not tool_context.state.get("current_corpus"):
                tool_context.state["current_corpus"] = c.get("display_name", corpus_name)
            return True
    return False


def _corpus_id_from_resource(resource_name: str) -> str:
    return resource_name.split("/")[-1]


def _get_collection(corpus_id: str):
    client = _client()
    return client.get_collection(name=_collection_name(corpus_id))


def list_corpora_dict() -> dict[str, Any]:
    try:
        registry = _load_registry()
        corpus_info: list[dict[str, Any]] = []
        for c in registry.get("corpora", []):
            corpus_info.append(
                {
                    "resource_name": c["resource_name"],
                    "display_name": c.get("display_name", ""),
                    "create_time": c.get("created_at", ""),
                    "update_time": c.get("updated_at", c.get("created_at", "")),
                }
            )
        return {
            "status": "success",
            "message": f"Found {len(corpus_info)} local corpora",
            "corpora": corpus_info,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "corpora": []}


def create_corpus_dict(display_name: str, tool_context: ToolContext) -> dict[str, Any]:
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", display_name)
    registry = _load_registry()
    if _find_corpus_entry(registry, display_name=clean):
        return {
            "status": "info",
            "message": f"Corpus '{clean}' already exists",
            "corpus_name": clean,
            "corpus_created": False,
        }

    corpus_id = str(uuid.uuid4())
    resource_name = _resource_name(corpus_id)
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "corpus_id": corpus_id,
        "display_name": clean,
        "resource_name": resource_name,
        "created_at": now,
        "updated_at": now,
    }
    registry.setdefault("corpora", []).append(entry)
    _save_registry(registry)

    client = _client()
    client.get_or_create_collection(
        name=_collection_name(corpus_id),
        metadata={"display_name": clean, "corpus_id": corpus_id},
    )

    tool_context.state[f"corpus_exists_{clean}"] = True
    tool_context.state[f"corpus_exists_{resource_name}"] = True
    tool_context.state["current_corpus"] = clean

    return {
        "status": "success",
        "message": f"Successfully created local corpus '{clean}'",
        "corpus_name": resource_name,
        "display_name": clean,
        "corpus_created": True,
    }


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text.strip():
        return []
    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(text), step):
        piece = text[i : i + chunk_size]
        if piece.strip():
            chunks.append(piece)
    return chunks


def _bytes_to_text(data: bytes, source: str) -> str:
    lower = source.lower()
    if lower.endswith(".pdf") or data[:4] == b"%PDF":
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t:
                parts.append(t)
        return "\n".join(parts)
    return data.decode("utf-8", errors="replace")


def _load_bytes_from_uri(uri: str) -> tuple[bytes, str]:
    u = uri.strip()
    if u.startswith("gs://"):
        from google.cloud import storage

        rest = u[5:]
        if "/" not in rest:
            raise ValueError("Invalid gs:// URI (need bucket/path)")
        bucket_name, blob_path = rest.split("/", 1)
        client = storage.Client()
        blob = client.bucket(bucket_name).blob(blob_path)
        return blob.download_as_bytes(), u

    if u.startswith("http://") or u.startswith("https://"):
        with httpx.Client(follow_redirects=True, timeout=120.0) as client:
            r = client.get(u)
            r.raise_for_status()
            return r.content, u

    p = Path(u)
    if p.is_file():
        return p.read_bytes(), str(p.resolve())

    raise ValueError(f"Unsupported or missing path: {uri}")


def import_paths_dict(
    corpus_resource_name: str,
    paths: list[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    cfg = _cfg()
    corpus_id = _corpus_id_from_resource(corpus_resource_name)
    registry = _load_registry()
    entry = _find_corpus_entry(registry, corpus_id=corpus_id)
    if not entry:
        return {
            "status": "error",
            "message": f"Corpus not found for resource {corpus_resource_name}",
            "corpus_name": corpus_resource_name,
            "paths": paths,
        }

    collection = _get_collection(corpus_id)
    added_files = 0
    invalid: list[str] = []
    conversions: list[str] = []

    for raw_path in paths:
        try:
            data, resolved = _load_bytes_from_uri(raw_path)
            text = _bytes_to_text(data, resolved)
            chunks = _chunk_text(text, cfg.DEFAULT_CHUNK_SIZE, cfg.DEFAULT_CHUNK_OVERLAP)
            if not chunks:
                invalid.append(f"{raw_path} (no extractable text)")
                continue

            doc_id = str(uuid.uuid4())
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": doc_id,
                    "source_uri": resolved,
                    "chunk_index": i,
                    "display_name": Path(resolved.split("?")[0]).name or resolved,
                }
                for i in range(len(chunks))
            ]
            collection.add(ids=ids, documents=chunks, metadatas=metadatas)
            added_files += 1
        except Exception as e:
            logger.exception("Ingest failed for %s", raw_path)
            invalid.append(f"{raw_path} ({e})")

    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_registry(registry)

    if not tool_context.state.get("current_corpus"):
        tool_context.state["current_corpus"] = entry["display_name"]

    msg = f"Added {added_files} file(s) to local corpus '{entry['display_name']}'"
    if invalid:
        msg += f"; skipped/failed: {len(invalid)}"

    return {
        "status": "success" if added_files else "error",
        "message": msg,
        "corpus_name": entry["display_name"],
        "files_added": added_files,
        "paths": paths,
        "invalid_paths": invalid,
        "conversions": conversions,
    }


def rag_query_dict(corpus_resource_name: str, query: str) -> dict[str, Any]:
    cfg = _cfg()
    corpus_id = _corpus_id_from_resource(corpus_resource_name)
    try:
        collection = _get_collection(corpus_id)
    except Exception:
        return {
            "status": "error",
            "message": "Corpus collection not found",
            "query": query,
            "corpus_name": corpus_resource_name,
        }

    n = min(cfg.DEFAULT_TOP_K, max(1, collection.count())) if collection.count() else cfg.DEFAULT_TOP_K
    if collection.count() == 0:
        return {
            "status": "warning",
            "message": "Corpus is empty; add documents first.",
            "query": query,
            "corpus_name": corpus_resource_name,
            "results": [],
            "results_count": 0,
        }

    res = collection.query(query_texts=[query], n_results=n, include=["documents", "metadatas", "distances"])
    results: list[dict[str, Any]] = []
    if res["documents"] and res["documents"][0]:
        docs0 = res["documents"][0]
        meta0 = res["metadatas"][0] if res.get("metadatas") else [{}] * len(docs0)
        dist0 = res["distances"][0] if res.get("distances") else [0.0] * len(docs0)
        for doc, meta, dist in zip(docs0, meta0, dist0):
            d = float(dist) if dist is not None else 0.0
            score = 1.0 / (1.0 + d)
            results.append(
                {
                    "source_uri": meta.get("source_uri", "") if meta else "",
                    "source_name": meta.get("display_name", "") if meta else "",
                    "text": doc or "",
                    "score": score,
                }
            )

    if not results:
        return {
            "status": "warning",
            "message": f"No results for query: {query!r}",
            "query": query,
            "corpus_name": corpus_resource_name,
            "results": [],
            "results_count": 0,
        }

    return {
        "status": "success",
        "message": "Query completed",
        "query": query,
        "corpus_name": corpus_resource_name,
        "results": results,
        "results_count": len(results),
    }


def get_corpus_info_dict(corpus_resource_name: str, corpus_display_key: str) -> dict[str, Any]:
    corpus_id = _corpus_id_from_resource(corpus_resource_name)
    registry = _load_registry()
    entry = _find_corpus_entry(registry, corpus_id=corpus_id)
    if not entry:
        return {"status": "error", "message": "Corpus not found", "corpus_name": corpus_display_key}

    try:
        collection = _get_collection(corpus_id)
        rows = collection.get(include=["metadatas"])
    except Exception as e:
        return {"status": "error", "message": str(e), "corpus_name": corpus_display_key}

    metas = rows.get("metadatas") or []
    by_doc: dict[str, dict[str, Any]] = {}
    for m in metas:
        if not m:
            continue
        did = m.get("document_id")
        if not did:
            continue
        if did not in by_doc:
            by_doc[did] = {
                "file_id": did,
                "display_name": m.get("display_name", ""),
                "source_uri": m.get("source_uri", ""),
                "create_time": "",
                "update_time": "",
            }

    file_details = list(by_doc.values())
    return {
        "status": "success",
        "message": f"Corpus '{entry['display_name']}' has {len(file_details)} document(s)",
        "corpus_name": corpus_display_key,
        "corpus_display_name": entry["display_name"],
        "file_count": len(file_details),
        "files": file_details,
    }


def delete_document_dict(corpus_resource_name: str, document_id: str) -> dict[str, Any]:
    corpus_id = _corpus_id_from_resource(corpus_resource_name)
    collection = _get_collection(corpus_id)
    collection.delete(where={"document_id": document_id})
    return {
        "status": "success",
        "message": f"Deleted document {document_id}",
        "corpus_name": corpus_resource_name,
        "document_id": document_id,
    }


def delete_corpus_dict(corpus_resource_name: str, tool_context: ToolContext) -> dict[str, Any]:
    corpus_id = _corpus_id_from_resource(corpus_resource_name)
    registry = _load_registry()
    entry = _find_corpus_entry(registry, corpus_id=corpus_id)
    if not entry and registry.get("corpora"):
        entry = _find_corpus_entry(registry, resource_name=corpus_resource_name)
    if not entry:
        return {"status": "error", "message": "Corpus not found", "corpus_name": corpus_resource_name}

    display_name = entry.get("display_name", "")
    resource_name = entry["resource_name"]

    registry["corpora"] = [c for c in registry.get("corpora", []) if c.get("corpus_id") != corpus_id]
    _save_registry(registry)

    try:
        _client().delete_collection(name=_collection_name(corpus_id))
    except Exception as e:
        logger.warning("Chroma delete_collection: %s", e)

    for key in (
        f"corpus_exists_{resource_name}",
        f"corpus_exists_{display_name}",
    ):
        if key in tool_context.state:
            del tool_context.state[key]

    return {"status": "success", "message": "Corpus deleted", "corpus_name": corpus_resource_name}
