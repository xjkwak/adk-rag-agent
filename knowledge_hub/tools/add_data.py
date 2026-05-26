"""
Tool for adding new data sources to a RAG corpus (Vertex or local Chroma).
"""

import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse

from google.adk.tools.tool_context import ToolContext

from ..config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBEDDING_REQUESTS_PER_MIN,
    PROJECT_ID,
    USE_LOCAL_RAG,
)
from .utils import check_corpus_exists, get_corpus_resource_name

_DATA_INGESTION_DOC = (
    "https://cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/use-data-ingestion"
)


def _https_public_storage_to_gs(uri: str) -> Optional[str]:
    """Map public HTTPS object URLs to gs://bucket/object for Vertex RAG import."""
    raw = (uri or "").strip()
    if not raw.lower().startswith("http"):
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    path = (parsed.path or "").lstrip("/")
    if not path:
        return None

    # https://storage.googleapis.com/BUCKET/OBJECT_PATH
    if host == "storage.googleapis.com":
        if "/" not in path:
            return None
        bucket, object_path = path.split("/", 1)
        if not bucket or not object_path:
            return None
        return f"gs://{bucket}/{unquote(object_path)}"

    # https://BUCKET.storage.googleapis.com/OBJECT_PATH
    if host.endswith(".storage.googleapis.com"):
        suffix = ".storage.googleapis.com"
        if not host.endswith(suffix) or host == suffix:
            return None
        bucket = host[: -len(suffix)]
        if not bucket or not path:
            return None
        return f"gs://{bucket}/{unquote(path)}"

    return None


def _format_exception_chain(exc: BaseException, max_depth: int = 8) -> str:
    parts: List[str] = [str(exc)]
    seen: set[int] = {id(exc)}
    cur: BaseException | None = exc
    depth = 0
    while depth < max_depth:
        nxt = cur.__cause__ or cur.__context__
        if nxt is None or id(nxt) in seen:
            break
        seen.add(id(nxt))
        parts.append(str(nxt))
        cur = nxt
        depth += 1
    return " | ".join(parts)


def _drive_import_troubleshooting_hint(paths: List[str]) -> str:
    """Extra context when Vertex returns vague INTERNAL errors on Drive import."""
    if not any("drive.google.com" in (p or "") for p in paths):
        return ""
    proj = PROJECT_ID or "<your GCP project id>"
    return (
        " For Google Drive files, Vertex reads the file as the **Vertex AI RAG Data Service Agent** "
        f"for project `{proj}` (not as your user). In Cloud Console → **IAM**, enable "
        "**Include Google-provided role grants**, open **Vertex AI RAG Data Service Agent**, "
        "and copy its email exactly. The address uses your numeric **project number**, not the "
        f"project id string: `service-<PROJECT_NUMBER>@gcp-sa-vertex-rag.iam.gserviceaccount.com`. "
        f"Get the number with: `gcloud projects describe {proj} --format='value(projectNumber)'` "
        "(if `proj` is your project id). Share the Drive file or folder with **Viewer** to that email; "
        "wait several minutes after sharing. Avoid **Shared drives** if problems persist. "
        "If it still fails: export native Google Docs/Sheets to **PDF** (or another supported binary), "
        "upload that file to Drive or copy it to **Cloud Storage** and import with a `gs://bucket/object` "
        "URI (often more reliable than Drive). Check **Cloud Logging** (Vertex AI / RAG import) for the "
        f"underlying error. Doc: {_DATA_INGESTION_DOC}"
    )


def add_data(
    corpus_name: str,
    paths: List[str],
    tool_context: ToolContext,
) -> dict:
    """
    Add new data sources to a Vertex AI RAG corpus.

    Args:
        corpus_name (str): The name of the corpus to add data to. If empty, the current corpus will be used.
        paths (List[str]): List of URLs or GCS paths to add to the corpus.
                          Supported formats:
                          - Google Drive: "https://drive.google.com/file/d/{FILE_ID}/view"
                          - Google Docs/Sheets/Slides: "https://docs.google.com/{type}/d/{FILE_ID}/..."
                          - Google Cloud Storage: "gs://{BUCKET}/{PATH}"
                          - Public GCS HTTPS: "https://storage.googleapis.com/{BUCKET}/{OBJECT}" or
                            "https://{BUCKET}.storage.googleapis.com/{OBJECT}" (converted to gs://)
                          Example: ["https://drive.google.com/file/d/123", "gs://my_bucket/my_files_dir"]
        tool_context (ToolContext): The tool context

    Returns:
        dict: Information about the added data and status
    """
    # Check if the corpus exists
    if not check_corpus_exists(corpus_name, tool_context):
        return {
            "status": "error",
            "message": f"Corpus '{corpus_name}' does not exist. Please create it first using the create_corpus tool.",
            "corpus_name": corpus_name,
            "paths": paths,
        }

    # Validate inputs
    if not paths or not all(isinstance(path, str) for path in paths):
        return {
            "status": "error",
            "message": "Invalid paths: Please provide a list of URLs or GCS paths",
            "corpus_name": corpus_name,
            "paths": paths,
        }

    # Pre-process paths to validate and convert Google Docs URLs to Drive format if needed
    validated_paths = []
    invalid_paths = []
    conversions = []

    for path in paths:
        if not path or not isinstance(path, str):
            invalid_paths.append(f"{path} (Not a valid string)")
            continue

        if USE_LOCAL_RAG:
            if re.match(r"https://docs\.google\.com/", path, re.I):
                invalid_paths.append(
                    f"{path} (Google Docs/Drive URLs are not supported in local RAG; use gs://, "
                    f"https://... to a PDF or text file, or an absolute file path)"
                )
                continue
            if re.match(r"https://drive\.google\.com/", path, re.I):
                invalid_paths.append(
                    f"{path} (Google Drive URLs are not supported in local RAG; use gs://, "
                    f"https://... to a PDF or text file, or an absolute file path)"
                )
                continue
            local_file = Path(path.strip()).expanduser()
            if local_file.is_file():
                validated_paths.append(str(local_file.resolve()))
                continue

        # Check for Google Docs/Sheets/Slides URLs and convert them to Drive format
        docs_match = re.match(
            r"https:\/\/docs\.google\.com\/(?:document|spreadsheets|presentation)\/d\/([a-zA-Z0-9_-]+)(?:\/|$)",
            path,
        )
        if docs_match:
            file_id = docs_match.group(1)
            drive_url = f"https://drive.google.com/file/d/{file_id}/view"
            validated_paths.append(drive_url)
            conversions.append(f"{path} → {drive_url}")
            continue

        # Check for valid Drive URL format
        drive_match = re.match(
            r"https:\/\/drive\.google\.com\/(?:file\/d\/|open\?id=)([a-zA-Z0-9_-]+)(?:\/|$)",
            path,
        )
        if drive_match:
            # Normalize to the standard Drive URL format
            file_id = drive_match.group(1)
            drive_url = f"https://drive.google.com/file/d/{file_id}/view"
            validated_paths.append(drive_url)
            if drive_url != path:
                conversions.append(f"{path} → {drive_url}")
            continue

        # Check for GCS paths
        if path.startswith("gs://"):
            validated_paths.append(path)
            continue

        # Public HTTPS URLs for Cloud Storage objects → gs://
        gs_from_https = _https_public_storage_to_gs(path)
        if gs_from_https:
            validated_paths.append(gs_from_https)
            if gs_from_https != path.strip():
                conversions.append(f"{path.strip()} → {gs_from_https}")
            continue

        # If we're here, the path wasn't in a recognized format
        invalid_paths.append(f"{path} (Invalid format)")

    # Check if we have any valid paths after validation
    if not validated_paths:
        if invalid_paths:
            hint = (
                " In local RAG mode (USE_LOCAL_RAG=1), use gs://, HTTPS links to PDF/text, public GCS HTTPS URLs, "
                "or absolute file paths — not Google Drive."
                if USE_LOCAL_RAG
                else " Use Google Drive URLs, gs:// URIs, public HTTPS GCS object URLs, or (Vertex only) supported formats."
            )
            msg = "Every path was rejected or unsupported: " + "; ".join(invalid_paths) + hint
        else:
            msg = (
                "No paths were given. In local RAG mode use gs://, HTTPS PDF/text, or a file path; "
                "with Vertex you can also use Google Drive URLs."
                if USE_LOCAL_RAG
                else "No valid paths provided. Please provide Google Drive URLs or GCS paths."
            )
        return {
            "status": "error",
            "message": msg,
            "corpus_name": corpus_name,
            "invalid_paths": invalid_paths,
        }

    try:
        # Get the corpus resource name
        corpus_resource_name = get_corpus_resource_name(corpus_name)

        if USE_LOCAL_RAG:
            from ..local_rag import store as local_store

            out = local_store.import_paths_dict(
                corpus_resource_name, validated_paths, tool_context
            )
            if conversions:
                out["conversions"] = conversions
            return out

        from vertexai import rag

        # Set up chunking configuration
        transformation_config = rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            ),
        )

        # Import files to the corpus
        import_result = rag.import_files(
            corpus_resource_name,
            validated_paths,
            transformation_config=transformation_config,
            max_embedding_requests_per_min=DEFAULT_EMBEDDING_REQUESTS_PER_MIN,
        )

        # Set this as the current corpus if not already set
        if not tool_context.state.get("current_corpus"):
            tool_context.state["current_corpus"] = corpus_name

        # Build the success message
        conversion_msg = ""
        if conversions:
            conversion_msg = " (Converted Google Docs URLs to Drive format)"

        return {
            "status": "success",
            "message": f"Successfully added {import_result.imported_rag_files_count} file(s) to corpus '{corpus_name}'{conversion_msg}",
            "corpus_name": corpus_name,
            "files_added": import_result.imported_rag_files_count,
            "paths": validated_paths,
            "invalid_paths": invalid_paths,
            "conversions": conversions,
        }

    except Exception as e:
        err = _format_exception_chain(e)
        hint = ""
        lowered = err.lower()
        if any(
            x in lowered
            for x in ("internal error", "500", "statuscode.internal", " 13:")
        ):
            hint = _drive_import_troubleshooting_hint(validated_paths)
        return {
            "status": "error",
            "message": f"Error adding data to corpus: {err}{hint}",
            "corpus_name": corpus_name,
            "paths": paths,
        }
