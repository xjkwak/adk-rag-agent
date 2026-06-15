#!/usr/bin/env python3
"""
Smoke-test Support Intake API endpoints (no Gemini/Jira calls for full E2E).

Usage:
  python scripts/validate_intake_flow.py [--base-url http://127.0.0.1:8080]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _post(base: str, path: str, body: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body or {}).encode() if body is not None else b""
    req = urllib.request.Request(
        url,
        data=data if body is not None else None,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _get(base: str, path: str) -> dict:
    url = f"{base.rstrip('/')}{path}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    base = args.base_url

    print("1. Create session…")
    session = _post(base, "/hub/intake/sessions")
    cid = session["conversation_id"]
    assert cid, "missing conversation_id"
    print(f"   OK conversation_id={cid}")

    print("2. GET session…")
    state = _get(base, f"/hub/intake/sessions/{cid}")
    assert state["conversationId"] == cid
    print("   OK")

    print("3. Send FAQ message (may call Gemini if configured)…")
    try:
        msg = _post(
            base,
            "/hub/intake/message",
            {
                "conversation_id": cid,
                "message": "How do I reset my password for the reporting system?",
            },
        )
        print(f"   status={msg['state'].get('status')}")
        print(f"   assistant preview: {msg['assistant_message'][:120]}…")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"   WARN message endpoint returned {e.code}: {body[:200]}")
        print("   (Expected if Gemini/Vertex is not configured locally)")

    print("\nValidation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
