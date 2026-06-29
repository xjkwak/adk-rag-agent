"""Compose multi-modal user input (text, audio transcript, attachments)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..adapters.attachments import ProcessedAttachment


@dataclass
class UserMultiInput:
    text: str | None = None
    transcript: str | None = None
    attachments: list[ProcessedAttachment] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(
            (self.text and self.text.strip())
            or (self.transcript and self.transcript.strip())
            or self.attachments
        )


def compose_user_message(user_input: UserMultiInput) -> tuple[str, dict[str, object]]:
    """Build chat content and metadata from combined inputs."""
    parts: list[str] = []
    text = (user_input.text or "").strip()
    transcript = (user_input.transcript or "").strip()

    if text:
        parts.append(text)

    if transcript:
        if text:
            parts.append(f"\n\n[Voice note transcript]\n{transcript}")
        else:
            parts.append(transcript)

    attachment_meta: list[dict[str, object]] = []
    for attachment in user_input.attachments:
        parts.append(
            f"\n\n--- Attached file: {attachment.filename} ---\n"
            f"{attachment.excerpt}"
        )
        attachment_meta.append(attachment.to_dict())

    content = "".join(parts).strip()
    metadata: dict[str, object] = {
        "inputType": "multi" if attachment_meta or transcript else "text",
        "hasAudio": bool(transcript),
        "attachments": attachment_meta,
    }
    if transcript and not text:
        metadata["inputType"] = "audio"
    if attachment_meta and not text and not transcript:
        metadata["inputType"] = "attachment"
    if attachment_meta and (text or transcript):
        metadata["inputType"] = "multi"

    return content, metadata
