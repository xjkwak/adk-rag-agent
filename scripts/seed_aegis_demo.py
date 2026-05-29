#!/usr/bin/env python3
"""
Create or refresh the aegis-demo corpus with the six Aegis PoC assets.

Usage (from repo root, with venv active):
  USE_LOCAL_RAG=1 python scripts/seed_aegis_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets"

AEGIS_DEMO_FILES = [
    "Aegis_SOP_IPC_Compliance.md",
    "Aegis_Manufacturing_Rules.md",
    "WorkOrderService.cs",
    "LineValidationService.cs",
    "sp_CloseWorkOrder.sql",
    "sp_ValidateLineClearance.sql",
]

CORPUS_DISPLAY_NAME = "aegis-demo"


class _ToolContext:
    def __init__(self) -> None:
        self.state: dict = {}


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "knowledge_hub" / ".env")

    from knowledge_hub.config import USE_LOCAL_RAG

    if not USE_LOCAL_RAG:
        print(
            "Set USE_LOCAL_RAG=1 in knowledge_hub/.env for local Chroma seeding.",
            file=sys.stderr,
        )
        return 1

    from knowledge_hub.local_rag import store as local_store

    ctx = _ToolContext()
    paths = [str(ASSETS / name) for name in AEGIS_DEMO_FILES]
    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        print("Missing asset files:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1

    registry = local_store._load_registry()
    entry = local_store._find_corpus_entry(registry, display_name=CORPUS_DISPLAY_NAME)
    if not entry:
        created = local_store.create_corpus_dict(CORPUS_DISPLAY_NAME, ctx)
        if created.get("status") not in ("success", "info"):
            print(f"Failed to create corpus: {created}", file=sys.stderr)
            return 1
        resource_name = created["corpus_name"]
        print(f"Created corpus '{CORPUS_DISPLAY_NAME}'")
    else:
        resource_name = entry["resource_name"]
        print(f"Corpus '{CORPUS_DISPLAY_NAME}' already exists; adding files")

    result = local_store.import_paths_dict(resource_name, paths, ctx)
    print(result.get("message", result))
    if result.get("invalid_paths"):
        for inv in result["invalid_paths"]:
            print(f"  skipped: {inv}", file=sys.stderr)

    corpus_id = local_store._corpus_id_from_resource(resource_name)
    collection = local_store._get_collection(corpus_id)
    count = collection.count()
    print(f"Chroma chunks in corpus: {count}")
    return 0 if result.get("status") == "success" and count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
