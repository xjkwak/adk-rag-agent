"""Environment configuration for Support Intake."""

import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def get_jira_settings() -> dict[str, str | bool]:
    """Read Jira config at call time so dotenv loads before ticket creation."""
    fixed_issue_key = _env("JIRA_FIXED_ISSUE_KEY").strip()
    return {
        "url": _env("JIRA_URL"),
        "username": _env("JIRA_USERNAME"),
        "api_token": _env("JIRA_API_TOKEN").strip(),
        "project_key": _env("JIRA_PROJECT_KEY", "CODEROAD"),
        "fixed_issue_key": fixed_issue_key,
        "read_only": _env("READ_ONLY_MODE", "false").lower() in ("1", "true", "yes"),
        "uvx_command": _env("UVX_COMMAND", "uvx"),
    }


# Module-level aliases (legacy); prefer get_jira_settings() for Jira ops
JIRA_URL = _env("JIRA_URL")
JIRA_USERNAME = _env("JIRA_USERNAME")
JIRA_API_TOKEN = _env("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = _env("JIRA_PROJECT_KEY", "CODEROAD")
JIRA_FIXED_ISSUE_KEY = _env("JIRA_FIXED_ISSUE_KEY")
READ_ONLY_MODE = _env("READ_ONLY_MODE", "false").lower() in ("1", "true", "yes")

SUPPORT_KB_CORPUS = _env("SUPPORT_KB_CORPUS", "support-kb")
STT_MODEL = _env("STT_MODEL", "gemini-2.5-flash")
NLU_MODEL = _env("NLU_MODEL", "gemini-2.5-flash")
INTAKE_KB_CONFIDENCE_THRESHOLD = float(
    _env("INTAKE_KB_CONFIDENCE_THRESHOLD", "0.72")
)

GOOGLE_CLOUD_PROJECT = _env("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = _env("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_GENAI_USE_VERTEXAI = _env("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() in (
    "1",
    "true",
    "yes",
)

UVX_COMMAND = _env("UVX_COMMAND", "uvx")
