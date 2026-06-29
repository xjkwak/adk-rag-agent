"""Jira issue create/update via mcp-atlassian MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from typing import Any

from ..config import get_jira_settings
from ..config_loader import get_jira_config
from ..orchestrator.field_heuristics import build_ticket_title_heuristic
from ..orchestrator.flows import (
    estimate_ticket_time,
    get_flow_config,
    get_flow_id,
    get_flow_label,
)
from ..orchestrator.state import TicketPreview

logger = logging.getLogger(__name__)

_mcp_lock = asyncio.Lock()
_ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")


def _jira_base_url(jira_url: str) -> str:
    return jira_url.rstrip("/")


def _validate_jira_config(settings: dict[str, str | bool]) -> None:
    missing = []
    if not settings.get("url"):
        missing.append("JIRA_URL")
    if not settings.get("username"):
        missing.append("JIRA_USERNAME")
    if not settings.get("api_token"):
        missing.append("JIRA_API_TOKEN")
    if missing:
        raise ValueError(
            f"Missing Jira configuration: {', '.join(missing)}. "
            "Add them to knowledge_hub/.env (see .env.sample)."
        )
    if settings.get("read_only"):
        raise ValueError(
            "Jira is in read-only mode. Set READ_ONLY_MODE=false to create issues."
        )
    fixed_key = str(settings.get("fixed_issue_key", "")).strip()
    if fixed_key and not _ISSUE_KEY_PATTERN.match(fixed_key):
        raise ValueError(
            f"Invalid JIRA_FIXED_ISSUE_KEY '{fixed_key}'. "
            "Expected format like AITR-89."
        )


def _resolve_uvx_command(cmd: str) -> str:
    if shutil.which(cmd):
        return cmd
    local = os.path.expanduser("~/.local/bin/uvx")
    if os.path.isfile(local):
        return local
    raise RuntimeError(
        "uvx not found. Install uv (https://docs.astral.sh/uv/) or set UVX_COMMAND."
    )


def _mcp_server_env(settings: dict[str, str | bool]) -> dict[str, str]:
    return {
        "JIRA_URL": str(settings["url"]),
        "JIRA_USERNAME": str(settings["username"]),
        "JIRA_API_TOKEN": str(settings["api_token"]),
        "READ_ONLY_MODE": "false",
    }


def _parse_mcp_tool_result(result: Any) -> dict[str, Any]:
    if result.isError:
        texts = [
            block.text
            for block in (result.content or [])
            if hasattr(block, "text") and block.text
        ]
        raise RuntimeError(
            texts[0] if texts else "Jira MCP tool returned an error"
        )

    if result.content:
        for block in result.content:
            if hasattr(block, "text") and block.text:
                text = block.text.strip()
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    raise RuntimeError(f"Jira MCP tool error: {text}") from None
                if isinstance(parsed, dict) and "result" in parsed:
                    inner = (
                        json.loads(parsed["result"])
                        if isinstance(parsed["result"], str)
                        else parsed["result"]
                    )
                    return inner if isinstance(inner, dict) else parsed
                return parsed if isinstance(parsed, dict) else {"result": parsed}
    raise RuntimeError("Empty response from Jira MCP tool")


def _format_jira_api_error(
    status_code: int,
    body: str,
    settings: dict[str, str | bool],
    *,
    issue_key: str | None = None,
) -> str:
    """Turn Jira HTTP errors into actionable messages."""
    jira_url = str(settings.get("url", "")).rstrip("/")
    username = str(settings.get("username", ""))

    if status_code == 401:
        return (
            "Jira API authentication failed (401). "
            f"Check JIRA_USERNAME ({username}) and regenerate JIRA_API_TOKEN at "
            "https://id.atlassian.com/manage-profile/security/api-tokens "
            f"for the same Atlassian site as {jira_url}."
        )

    if status_code == 404 and issue_key:
        return (
            f"Cannot access Jira issue {issue_key} (404). "
            "This usually means the API credentials cannot see that issue — "
            "not that the ticket is missing. Verify JIRA_URL, JIRA_USERNAME, and "
            "JIRA_API_TOKEN in knowledge_hub/.env match the site where the issue "
            f"exists ({jira_url}), then restart the API server."
        )

    return f"Jira API error {status_code}: {body}"


async def _verify_jira_connection(settings: dict[str, str | bool]) -> None:
    """Fail fast when credentials cannot authenticate."""
    import httpx

    jira_url = str(settings["url"])
    jira_username = str(settings["username"])
    jira_token = str(settings["api_token"])
    base = _jira_base_url(jira_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{base}/rest/api/3/myself",
            auth=(jira_username, jira_token),
            headers={"Accept": "application/json"},
        )
        if resp.status_code == 401:
            raise RuntimeError(
                _format_jira_api_error(401, resp.text, settings)
            )
        if resp.status_code >= 400:
            raise RuntimeError(
                _format_jira_api_error(resp.status_code, resp.text, settings)
            )


async def _verify_issue_access(
    settings: dict[str, str | bool], issue_key: str
) -> None:
    """Confirm the configured credentials can read the fixed issue."""
    import httpx

    jira_url = str(settings["url"])
    jira_username = str(settings["username"])
    jira_token = str(settings["api_token"])
    base = _jira_base_url(jira_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{base}/rest/api/3/issue/{issue_key}",
            params={"fields": "summary"},
            auth=(jira_username, jira_token),
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                _format_jira_api_error(
                    resp.status_code, resp.text, settings, issue_key=issue_key
                )
            )


def _preview_additional_fields(preview: TicketPreview) -> dict[str, Any]:
    additional: dict[str, Any] = {}
    if preview.priority:
        additional["priority"] = {"name": preview.priority}
    labels = list(preview.labels or [])
    if preview.environment:
        labels.append(f"env-{preview.environment.lower().replace(' ', '-')}")
    if labels:
        additional["labels"] = labels
    return additional


async def _call_mcp_tool(
    settings: dict[str, str | bool], tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    uvx = _resolve_uvx_command(str(settings["uvx_command"]))
    server_params = StdioServerParameters(
        command=uvx,
        args=["mcp-atlassian"],
        env=_mcp_server_env(settings),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            return _parse_mcp_tool_result(result)


async def _create_via_mcp(
    preview: TicketPreview, settings: dict[str, str | bool]
) -> dict[str, Any]:
    project_key = str(settings["project_key"])
    additional = _preview_additional_fields(preview)

    args: dict[str, Any] = {
        "project_key": project_key,
        "summary": preview.summary,
        "issue_type": preview.issue_type,
        "description": preview.description,
    }
    if additional:
        args["additional_fields"] = json.dumps(additional)

    return await _call_mcp_tool(settings, "jira_create_issue", args)


async def _update_via_mcp(
    preview: TicketPreview, settings: dict[str, str | bool], issue_key: str
) -> dict[str, Any]:
    fields = {
        "summary": preview.summary,
        "description": preview.description,
    }
    args: dict[str, Any] = {
        "issue_key": issue_key,
        "fields": json.dumps(fields),
    }
    additional = _preview_additional_fields(preview)
    if additional:
        args["additional_fields"] = json.dumps(additional)

    await _call_mcp_tool(settings, "jira_update_issue", args)
    base = _jira_base_url(str(settings["url"]))
    return {
        "key": issue_key,
        "url": f"{base}/browse/{issue_key}",
        "updated": True,
    }


async def _create_via_rest(
    preview: TicketPreview, settings: dict[str, str | bool]
) -> dict[str, Any]:
    """Fallback: Jira REST API v3 when MCP subprocess unavailable."""
    import httpx

    jira_url = str(settings["url"])
    jira_username = str(settings["username"])
    jira_token = str(settings["api_token"])
    project_key = str(settings["project_key"])
    base = _jira_base_url(jira_url)

    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": preview.summary,
        "issuetype": {"name": preview.issue_type},
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": preview.description[:32000]}],
                }
            ],
        },
    }
    if preview.labels:
        fields["labels"] = preview.labels
    if preview.priority:
        fields["priority"] = {"name": preview.priority}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base}/rest/api/3/issue",
            json={"fields": fields},
            auth=(jira_username, jira_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                _format_jira_api_error(resp.status_code, resp.text, settings)
            )
        data = resp.json()
        key = data.get("key", "")
        return {
            "key": key,
            "id": data.get("id"),
            "self": data.get("self"),
            "url": f"{base}/browse/{key}",
        }


async def _fetch_issue_description(
    settings: dict[str, str | bool], issue_key: str
) -> str:
    """Fetch plain-text description for appending demo intake updates."""
    import httpx

    jira_url = str(settings["url"])
    jira_username = str(settings["username"])
    jira_token = str(settings["api_token"])
    base = _jira_base_url(jira_url)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{base}/rest/api/3/issue/{issue_key}",
            params={"fields": "description"},
            auth=(jira_username, jira_token),
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            return ""
        data = resp.json()
        desc = data.get("fields", {}).get("description")
        if isinstance(desc, str):
            return desc
        if isinstance(desc, dict):
            # ADF -> rough plain text for append
            parts: list[str] = []

            def walk(node: Any) -> None:
                if isinstance(node, dict):
                    if node.get("type") == "text" and node.get("text"):
                        parts.append(str(node["text"]))
                    for child in node.get("content", []):
                        walk(child)

            walk(desc)
            return "\n".join(parts).strip()
    return ""


async def _update_via_rest(
    preview: TicketPreview, settings: dict[str, str | bool], issue_key: str
) -> dict[str, Any]:
    import httpx

    jira_url = str(settings["url"])
    jira_username = str(settings["username"])
    jira_token = str(settings["api_token"])
    base = _jira_base_url(jira_url)

    existing = await _fetch_issue_description(settings, issue_key)
    stamp = preview.description.strip()
    if existing:
        combined = f"{existing.rstrip()}\n\n---\n\n**Support Intake update**\n{stamp}"
    else:
        combined = stamp

    fields: dict[str, Any] = {
        "summary": preview.summary,
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": combined[:32000]}],
                }
            ],
        },
    }
    if preview.labels:
        fields["labels"] = preview.labels
    if preview.priority:
        fields["priority"] = {"name": preview.priority}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.put(
            f"{base}/rest/api/3/issue/{issue_key}",
            json={"fields": fields},
            auth=(jira_username, jira_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                _format_jira_api_error(
                    resp.status_code, resp.text, settings, issue_key=issue_key
                )
            )

    return {
        "key": issue_key,
        "url": f"{base}/browse/{issue_key}",
        "updated": True,
    }


async def submit_jira_ticket(preview: TicketPreview) -> dict[str, Any]:
    """Create a new Jira issue, or update JIRA_FIXED_ISSUE_KEY when configured."""
    settings = get_jira_settings()
    _validate_jira_config(settings)
    fixed_key = str(settings.get("fixed_issue_key", "")).strip()

    await _verify_jira_connection(settings)
    if fixed_key:
        await _verify_issue_access(settings, fixed_key)
        logger.info("Demo mode: updating fixed Jira issue %s", fixed_key)

    async with _mcp_lock:
        if fixed_key:
            try:
                result = await _update_via_mcp(preview, settings, fixed_key)
                result.setdefault("key", fixed_key)
                return result
            except Exception as exc:
                logger.warning("MCP Jira update failed (%s), trying REST fallback", exc)
                result = await _update_via_rest(preview, settings, fixed_key)
                result.setdefault("key", fixed_key)
                return result
        try:
            return await _create_via_mcp(preview, settings)
        except Exception as exc:
            logger.warning("MCP Jira create failed (%s), trying REST fallback", exc)
            return await _create_via_rest(preview, settings)


async def create_jira_issue(preview: TicketPreview) -> dict[str, Any]:
    """Backward-compatible alias for submit_jira_ticket."""
    return await submit_jira_ticket(preview)


def is_fixed_issue_mode() -> bool:
    return bool(get_jira_settings().get("fixed_issue_key"))


def build_ticket_preview(
    collected_fields: dict[str, Any],
    request_type: str,
    description: str,
    summary: str | None = None,
) -> TicketPreview:
    jira_cfg = get_jira_config()
    flow_cfg = get_flow_config(request_type)
    defaults = jira_cfg.get("defaults", {}).get(request_type, {})
    issue_type = flow_cfg.get("issue_type") or defaults.get("issue_type", "Task")
    labels = list(jira_cfg.get("labels", ["support-intake"]))
    labels.append(request_type.replace("_", "-"))
    flow_id = get_flow_id(request_type)
    flow_label = get_flow_label(request_type)
    time_estimate = estimate_ticket_time(request_type)

    title = summary or build_ticket_title_heuristic(collected_fields, request_type)
    description_body = description.rstrip()
    if time_estimate and "**Rough time estimate:**" not in description_body:
        description_body = (
            f"{description_body}\n\n"
            f"**Rough time estimate:** {time_estimate} "
            "(placeholder for sprint planning)"
        )

    return TicketPreview(
        summary=title,
        description=description_body,
        issue_type=issue_type,
        request_type=request_type,
        priority=collected_fields.get("priority"),
        environment=collected_fields.get("environment"),
        labels=labels,
        additional_info={
            k: v
            for k, v in collected_fields.items()
            if v is not None and k not in ("summary",)
        },
        intake_flow=flow_id,
        flow_label=flow_label,
        time_estimate=time_estimate,
    )


def extract_issue_key(result: dict[str, Any]) -> tuple[str, str]:
    settings = get_jira_settings()
    fixed_key = str(settings.get("fixed_issue_key", "")).strip()
    key = result.get("key") or result.get("issue_key") or fixed_key or ""
    url = result.get("url") or result.get("browse_url") or ""
    if not url and key:
        url = f"{_jira_base_url(str(settings['url']))}/browse/{key}"
    return key, url
