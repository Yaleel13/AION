"""Read-only stdio MCP bridge to the owner-authorized local runtime."""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations

mcp = MCPServer("AION runtime status")


def _error(message: str) -> CallToolResult:
    return CallToolResult(is_error=True, content=[TextContent(type="text", text=message)])


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                     idempotent_hint=True, open_world_hint=False))
async def runtime_status() -> CallToolResult:
    """Read AION runtime status through its owner policy. Accepts no commands or arguments."""
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        return _error("Policy denied: AION_OWNER_TOKEN is not configured.")
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.get(
                "http://127.0.0.1:8000/owner/runtime/status",
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code in {401, 403, 503}:
            return _error("Policy denied: runtime owner authorization unavailable or rejected.")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if data.get("source") != "runtime_status" or data.get("ok") is not True:
            return _error("Runtime returned an invalid status response.")
    except (httpx.HTTPError, ValueError, AttributeError):
        return _error("AION runtime is disconnected or unavailable.")
    return CallToolResult(content=[TextContent(type="text", text=response.text)], structured_content=data)


if __name__ == "__main__":
    mcp.run(transport="stdio")
