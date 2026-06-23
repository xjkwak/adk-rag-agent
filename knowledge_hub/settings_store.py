"""Persisted Knowledge HUB agent and UI configuration."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_ACTIVE_CORPUS_START = "<!-- ACTIVE_CORPUS_START -->"
_ACTIVE_CORPUS_END = "<!-- ACTIVE_CORPUS_END -->"

from .peakrock_instruction import PEAKROCK_INSTRUCTION
from .vertex_models import STATIC_VERTEX_GEMINI_MODELS, get_available_gemini_models

DEFAULT_MODEL = "gemini-2.5-flash"

# Backward-compatible alias; prefer get_available_gemini_models() for the UI.
AVAILABLE_GEMINI_MODELS: list[str] = STATIC_VERTEX_GEMINI_MODELS

DEFAULT_CORPUS = os.environ.get("KNOWLEDGE_HUB_DEFAULT_CORPUS", "peakrock-demo")

_repo_root = Path(__file__).resolve().parent.parent
_default_settings_dir = _repo_root / "data"
SETTINGS_DIR = Path(
    os.environ.get("KNOWLEDGE_HUB_SETTINGS_DIR", str(_default_settings_dir))
).expanduser()
SETTINGS_PATH = SETTINGS_DIR / "agent_settings.json"


def _default_settings() -> dict[str, Any]:
    return {
        "model": DEFAULT_MODEL,
        "instruction": PEAKROCK_INSTRUCTION.strip(),
        "default_corpus": DEFAULT_CORPUS,
    }


def _ensure_dir() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _active_corpus_section(corpus: str) -> str:
    return f"""{_ACTIVE_CORPUS_START}
## ACTIVE CORPUS (from Configuration — mandatory for chat)

Your **only** knowledge base in chat is corpus **`{corpus}`** (set on the Configuration page).

- For **every** `rag_query` and `get_corpus_info` call: use `corpus_name` = **`{corpus}`** (or empty string — tools resolve to this corpus).
- **Never** call `list_corpora` in chat. Do not enumerate other corpora. Corpus choice is configured in the UI, not in conversation.
- Questions such as "what are my documents", "what files do you have", "what is indexed", "list my documents" → call **`get_corpus_info`** on **`{corpus}`** and answer from that result only.
- If the user asks to use a different corpus, tell them to change **Default corpus for chat** under Configuration.
{_ACTIVE_CORPUS_END}"""


def strip_active_corpus_section(text: str) -> str:
    """Remove injected active-corpus block (for persisted / editable instruction)."""
    pattern = (
        re.escape(_ACTIVE_CORPUS_START) + r".*?" + re.escape(_ACTIVE_CORPUS_END)
    )
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def build_runtime_instruction(base_instruction: str | None = None) -> str:
    """Instruction sent to the agent, with current default corpus enforced."""
    settings = load_settings()
    base = strip_active_corpus_section(
        (base_instruction if base_instruction is not None else settings["instruction"])
    )
    section = _active_corpus_section(settings["default_corpus"])
    return f"{base}\n\n{section}"


def load_settings() -> dict[str, Any]:
    """Load settings from disk, falling back to defaults."""
    defaults = _default_settings()
    if not SETTINGS_PATH.exists():
        return defaults

    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return defaults

    if not isinstance(raw, dict):
        return defaults

    model = raw.get("model", defaults["model"])
    allowed = get_available_gemini_models(include=str(model))
    if model not in allowed:
        model = defaults["model"]

    instruction = raw.get("instruction", defaults["instruction"])
    if not isinstance(instruction, str) or not instruction.strip():
        instruction = defaults["instruction"]
    instruction = strip_active_corpus_section(instruction)

    default_corpus = raw.get("default_corpus", defaults["default_corpus"])
    if not isinstance(default_corpus, str) or not default_corpus.strip():
        default_corpus = defaults["default_corpus"]

    return {
        "model": model,
        "instruction": instruction,
        "default_corpus": default_corpus,
    }


def save_settings(
    *,
    model: str | None = None,
    instruction: str | None = None,
    default_corpus: str | None = None,
) -> dict[str, Any]:
    """Merge and persist settings; returns the saved document."""
    current = load_settings()
    if model is not None:
        allowed = get_available_gemini_models(include=model)
        if model not in allowed:
            raise ValueError(f"Unsupported model: {model}")
        current["model"] = model
    if instruction is not None:
        current["instruction"] = strip_active_corpus_section(instruction.strip())
    if default_corpus is not None:
        current["default_corpus"] = default_corpus.strip()
    _ensure_dir()
    SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def get_agent_settings() -> dict[str, str]:
    """Model + runtime instruction for agent construction."""
    s = load_settings()
    return {
        "model": s["model"],
        "instruction": build_runtime_instruction(s["instruction"]),
    }


def reset_agent_settings() -> dict[str, Any]:
    """Reset model, instruction, and default corpus to shipped defaults."""
    defaults = _default_settings()
    return save_settings(
        model=defaults["model"],
        instruction=defaults["instruction"],
        default_corpus=defaults["default_corpus"],
    )


def get_default_corpus() -> str:
    """Display name of the configured default RAG corpus."""
    return load_settings()["default_corpus"]
