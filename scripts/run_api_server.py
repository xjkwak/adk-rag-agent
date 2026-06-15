#!/usr/bin/env python3
"""Production ADK API server (no reload — suitable for Cloud Run)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load env before support_intake / knowledge_hub config modules read os.environ
_repo_root = Path(__file__).resolve().parent.parent
load_dotenv(_repo_root / "knowledge_hub" / ".env")
load_dotenv(_repo_root / ".env")

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# Repo root in container: /app (parent of scripts/)
# Only subdirs with agent packages (exclude scripts/, assets/)
_default_agents = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS_DIR = os.environ.get("AGENTS_DIR", _default_agents)
PORT = int(os.environ.get("PORT", os.environ.get("ADK_API_PORT", "8080")))
_origins = os.environ.get("ALLOW_ORIGINS", "*")
ALLOW_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()] or None

app = get_fast_api_app(
    agent_dir=AGENTS_DIR,
    session_db_url=os.environ.get("SESSION_DB_URL", ""),
    allow_origins=ALLOW_ORIGINS,
    web=False,
    trace_to_cloud=os.environ.get("TRACE_TO_CLOUD", "").lower() in ("1", "true", "yes"),
)

from knowledge_hub.admin_api import router as hub_config_router
from support_intake.api import router as intake_router

app.include_router(hub_config_router, prefix="/hub/config", tags=["hub-config"])
app.include_router(intake_router, prefix="/hub/intake", tags=["support-intake"])

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
