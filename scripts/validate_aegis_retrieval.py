#!/usr/bin/env python3
"""Smoke-test aegis-demo retrieval for PoC golden scenarios."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

QUERIES = [
    (
        "line_clearance",
        "line clearance validation before production SOP WorkOrder LineValidation",
    ),
    (
        "work_order_audit",
        "work order close audit trail stored procedure traceability",
    ),
    (
        "msl_traceability",
        "MSL moisture sensitivity traceability UID as-built",
    ),
]


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "knowledge_hub" / ".env")

    from knowledge_hub.config import USE_LOCAL_RAG

    if not USE_LOCAL_RAG:
        print("USE_LOCAL_RAG=1 required", file=sys.stderr)
        return 1

    from knowledge_hub.local_rag import store as local_store

    registry = local_store._load_registry()
    entry = local_store._find_corpus_entry(registry, display_name="aegis-demo")
    if not entry:
        print("aegis-demo corpus not found; run scripts/seed_aegis_demo.py", file=sys.stderr)
        return 1

    resource = entry["resource_name"]
    ok = True
    for label, query in QUERIES:
        result = local_store.rag_query_dict(resource, query)
        count = result.get("results_count", 0)
        sources = {r.get("source_name", "") for r in result.get("results", [])}
        print(f"\n[{label}] results={count} sources={sorted(sources)}")
        if count < 2:
            ok = False
            print("  WARN: expected at least 2 chunks for cross-doc synthesis")
        md = any(s.endswith(".md") for s in sources)
        code = any(s.endswith((".cs", ".sql")) for s in sources)
        if label == "line_clearance" and not (md and code):
            ok = False
            print("  WARN: expected both .md and code/sql sources")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
