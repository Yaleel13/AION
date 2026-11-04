"""Mode-scoped stdio MCP bridge to the loopback AION runtime."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.types import CallToolResult, TextContent, ToolAnnotations

OWNER_MCP_MODE = "owner"
AGENT_MCP_MODE = "agent"
MCP_MODE_ENV = "AION_MCP_MODE"


def _error(message: str, metadata: dict[str, str] | None = None) -> CallToolResult:
    return CallToolResult(is_error=True, content=[TextContent(type="text", text=message)], meta=metadata)


async def runtime_status() -> CallToolResult:
    """Read AION runtime status through its owner policy. Accepts no commands or arguments."""
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        return _error("Policy denied: AION_OWNER_TOKEN is not configured.")
    metadata = None
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.get(
                "http://127.0.0.1:8000/owner/runtime/status",
                headers={"Authorization": f"Bearer {token}"},
            )
        request_id = response.headers.get("x-aion-request-id", "")
        if re.fullmatch(r"[0-9a-f]{32}", request_id):
            metadata = {"aion/request_id": request_id}
        if response.status_code in {401, 403, 503}:
            return _error("Policy denied: runtime owner authorization unavailable or rejected.", metadata)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if data.get("source") != "runtime_status" or data.get("ok") is not True:
            return _error("Runtime returned an invalid status response.", metadata)
    except (httpx.HTTPError, ValueError, AttributeError):
        return _error("AION runtime is disconnected or unavailable.", metadata)
    return CallToolResult(content=[TextContent(type="text", text=response.text)], structured_content=data, meta=metadata)


async def runtime_syntax_approval_request() -> CallToolResult:
    """Submit one local agent request for a fixed runtime.syntax approval."""
    token = (os.getenv("AION_LOCAL_AGENT_TOKEN") or "").strip()
    if not token:
        return _error("Policy denied: AION_LOCAL_AGENT_TOKEN is not configured.")
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.post(
                "http://127.0.0.1:8000/agent/runtime-syntax-approvals",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code in {401, 403, 503}:
            return _error("Policy denied: local agent authorization unavailable or rejected.")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        execution_request_id = data.get("execution_request_id")
        if (
            not isinstance(execution_request_id, str)
            or not re.fullmatch(r"[0-9a-f]{32}", execution_request_id)
            or data.get("decision") != "pending"
        ):
            return _error("Runtime returned an invalid approval response.")
    except (httpx.HTTPError, ValueError, AttributeError):
        return _error("AION runtime is disconnected or unavailable.")
    result = {"execution_request_id": execution_request_id, "state": "pending"}
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result))],
        structured_content=result,
    )


async def runtime_syntax_approval_redeem(
    execution_request_id: str,
    ctx: Context,
) -> CallToolResult:
    """Redeem one approved local agent runtime.syntax approval."""
    params = ctx.request_context.params or {}
    arguments = params.get("arguments")
    if not isinstance(arguments, dict) or set(arguments) != {"execution_request_id"}:
        return _error("Policy denied: runtime syntax redemption accepts only an approval ID.")
    if not re.fullmatch(r"[0-9a-f]{32}", execution_request_id):
        return _error("Policy denied: invalid runtime syntax approval ID.")
    token = (os.getenv("AION_LOCAL_AGENT_TOKEN") or "").strip()
    if not token:
        return _error("Policy denied: AION_LOCAL_AGENT_TOKEN is not configured.")
    metadata = None
    try:
        async with httpx.AsyncClient(timeout=35, trust_env=False) as client:
            response = await client.post(
                f"http://127.0.0.1:8000/agent/runtime-syntax-approvals/{execution_request_id}/redeem",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        request_id = response.headers.get("x-aion-request-id", "")
        if re.fullmatch(r"[0-9a-f]{32}", request_id):
            metadata = {"aion/request_id": request_id}
        if response.status_code in {401, 403, 503}:
            return _error("Policy denied: runtime syntax approval cannot be redeemed.", metadata)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        status = data.get("status")
        if (
            data.get("job") != "runtime.syntax"
            or status not in {"succeeded", "failed", "timeout", "unavailable"}
            or data.get("ok") is not (status == "succeeded")
            or not isinstance(data.get("truncated"), bool)
        ):
            return _error("Runtime returned an invalid syntax redemption response.", metadata)
    except (httpx.HTTPError, ValueError, AttributeError):
        return _error("AION runtime is disconnected or unavailable.", metadata)
    result = {
        "execution_request_id": execution_request_id,
        "ok": data["ok"],
        "status": status,
        "truncated": data["truncated"],
    }
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result))],
        structured_content=result,
        meta=metadata,
    )


def agent_stdio_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the agent-mode process environment without owner credentials."""
    source = os.environ if environ is None else environ
    token = (source.get("AION_LOCAL_AGENT_TOKEN") or "").strip()
    if not token:
        raise ValueError("AION_LOCAL_AGENT_TOKEN is required for agent MCP mode")
    return {
        MCP_MODE_ENV: AGENT_MCP_MODE,
        "AION_LOCAL_AGENT_TOKEN": token,
    }


def create_mcp(mode: str | None = None) -> MCPServer:
    """Create one explicitly scoped MCP surface."""
    selected = (mode or os.getenv(MCP_MODE_ENV, OWNER_MCP_MODE)).strip().lower()
    if selected == OWNER_MCP_MODE:
        server = MCPServer("AION runtime status")
        server.tool(
            annotations=ToolAnnotations(
                read_only_hint=True,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=False,
            )
        )(runtime_status)
        return server
    if selected == AGENT_MCP_MODE:
        if (os.getenv("AION_OWNER_TOKEN") or "").strip():
            raise ValueError("Agent MCP mode must not receive AION_OWNER_TOKEN")
        server = MCPServer("AION runtime syntax approval requester")
        server.tool(
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=False,
                open_world_hint=False,
            )
        )(runtime_syntax_approval_request)
        server.tool(
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=False,
                open_world_hint=False,
            )
        )(runtime_syntax_approval_redeem)
        return server
    raise ValueError(f"{MCP_MODE_ENV} must be {OWNER_MCP_MODE!r} or {AGENT_MCP_MODE!r}")


mcp = create_mcp()


if __name__ == "__main__":
    mcp.run(transport="stdio")
