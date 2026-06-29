"""Extract text from user-uploaded support intake attachments."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 5
MAX_EXCERPT_CHARS = 8_000
MAX_TOTAL_EXCERPT_CHARS = 20_000

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "text/html",
    "text/xml",
    "application/json",
    "application/xml",
    "application/pdf",
    "application/octet-stream",
}

ALLOWED_EXTENSIONS = {
    ".txt",
    ".log",
    ".json",
    ".csv",
    ".md",
    ".xml",
    ".yaml",
    ".yml",
    ".pdf",
    ".html",
    ".htm",
    ".out",
    ".err",
}


@dataclass
class ProcessedAttachment:
    filename: str
    mime_type: str
    size_bytes: int
    text: str
    excerpt: str
    char_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "mimeType": self.mime_type,
            "sizeBytes": self.size_bytes,
            "excerpt": self.excerpt,
            "charCount": self.char_count,
        }


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    if dot < 0:
        return ""
    return filename[dot:].lower()


def _is_allowed(filename: str, mime_type: str | None) -> bool:
    ext = _extension(filename)
    if ext in ALLOWED_EXTENSIONS:
        return True
    if mime_type and mime_type.split(";")[0].strip() in ALLOWED_MIME_TYPES:
        return True
    return False


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def extract_attachment_text(
    filename: str,
    data: bytes,
    mime_type: str | None = None,
) -> str:
    if not data:
        raise ValueError(f"Attachment {filename!r} is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(
            f"Attachment {filename!r} is too large "
            f"({len(data)} bytes). Maximum is {MAX_FILE_BYTES}."
        )
    if not _is_allowed(filename, mime_type):
        raise ValueError(
            f"Unsupported attachment type for {filename!r}. "
            f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    ext = _extension(filename)
    content_type = (mime_type or "").split(";")[0].strip().lower()

    if ext == ".pdf" or content_type == "application/pdf":
        text = _extract_pdf_text(data)
    else:
        text = _decode_text(data)

    cleaned = text.strip()
    if not cleaned:
        raise ValueError(
            f"Could not extract readable text from {filename!r}."
        )
    return cleaned


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n… [truncated]"


def process_attachments(
    files: list[tuple[str, bytes, str | None]],
) -> list[ProcessedAttachment]:
    if len(files) > MAX_FILES:
        raise ValueError(
            f"Too many attachments ({len(files)}). Maximum is {MAX_FILES}."
        )

    processed: list[ProcessedAttachment] = []
    total_chars = 0

    for filename, data, mime_type in files:
        text = extract_attachment_text(filename, data, mime_type)
        remaining = MAX_TOTAL_EXCERPT_CHARS - total_chars
        if remaining <= 0:
            raise ValueError(
                "Combined attachment content exceeds the allowed limit."
            )
        per_file_limit = min(MAX_EXCERPT_CHARS, remaining)
        excerpt = _truncate(text, per_file_limit)
        total_chars += len(excerpt)
        processed.append(
            ProcessedAttachment(
                filename=filename,
                mime_type=(mime_type or "application/octet-stream").split(";")[0],
                size_bytes=len(data),
                text=text,
                excerpt=excerpt,
                char_count=len(text),
            )
        )
        logger.info(
            "Processed attachment %r (%d bytes -> %d chars)",
            filename,
            len(data),
            len(text),
        )

    return processed
