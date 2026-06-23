#!/usr/bin/env python3
"""
Create or refresh the amtech-demo corpus with assets from assets/Amtech/.

All regular files in that folder are ingested (PDF, markdown, etc.).

Usage (from repo root, with venv active):
  USE_LOCAL_RAG=1 python scripts/seed_amtech_demo.py
  USE_LOCAL_RAG=1 python scripts/seed_amtech_demo.py --incremental
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets" / "Amtech"

CORPUS_DISPLAY_NAME = "amtech-demo"


class _ToolContext:
    def __init__(self) -> None:
        self.state: dict = {}


def _amtech_asset_names() -> list[str]:
    if not ASSETS.is_dir():
        return []
    return sorted(
        p.name
        for p in ASSETS.iterdir()
        if p.is_file() and not p.name.startswith(".")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed amtech-demo corpus")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only add files not already indexed (default: full refresh)",
    )
    args = parser.parse_args()

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

    names = _amtech_asset_names()
    if not names:
        print(
            f"No files found in {ASSETS}. Add Amtech assets and retry.",
            file=sys.stderr,
        )
        return 1

    ctx = _ToolContext()
    paths = [str(ASSETS / name) for name in names]
    print(f"Ingesting {len(paths)} file(s) from {ASSETS.relative_to(REPO_ROOT)}/")

    registry = local_store._load_registry()
    entry = local_store._find_corpus_entry(registry, display_name=CORPUS_DISPLAY_NAME)
    if entry and not args.incremental:
        print(f"Refreshing corpus '{CORPUS_DISPLAY_NAME}' (delete and recreate)")
        deleted = local_store.delete_corpus_dict(entry["resource_name"], ctx)
        if deleted.get("status") != "success":
            print(f"Failed to delete corpus: {deleted}", file=sys.stderr)
            return 1
        entry = None

    if not entry:
        created = local_store.create_corpus_dict(CORPUS_DISPLAY_NAME, ctx)
        if created.get("status") not in ("success", "info"):
            print(f"Failed to create corpus: {created}", file=sys.stderr)
            return 1
        resource_name = created["corpus_name"]
        print(f"Created corpus '{CORPUS_DISPLAY_NAME}'")
    else:
        resource_name = entry["resource_name"]
        print(f"Corpus '{CORPUS_DISPLAY_NAME}' already exists; ingesting new files only")

    result = local_store.import_paths_dict(
        resource_name,
        paths,
        ctx,
        skip_existing=args.incremental,
    )
    print(result.get("message", result))
    if result.get("invalid_paths"):
        for inv in result["invalid_paths"]:
            print(f"  skipped: {inv}", file=sys.stderr)

    corpus_id = local_store._corpus_id_from_resource(resource_name)
    collection = local_store._get_collection(corpus_id)
    count = collection.count()
    print(f"Chroma chunks in corpus: {count}")
    added = int(result.get("files_added", 0))
    skipped = int(result.get("files_skipped", 0))
    if skipped and not added:
        print(f"All {skipped} file(s) were already indexed; no duplicates added.")
    return 0 if result.get("status") == "success" and count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
