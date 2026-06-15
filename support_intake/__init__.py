"""Support Intake Assistant — controlled conversational support intake workflow."""

from pathlib import Path

from dotenv import load_dotenv

_env_dir = Path(__file__).resolve().parent
load_dotenv(_env_dir / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / "knowledge_hub" / ".env")
load_dotenv(override=True)

from . import config  # noqa: E402

__all__ = ["config"]
