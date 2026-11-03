"""Exercise MCP dispatch and the real HTTP owner policy without a live service."""

import httpx
import pytest
from mcp import Client

from aion import mcp_server
from aion.main import app


@pytest.fixture
def runtime_transport(monkeypatch):
    original_client = httpx.AsyncClient
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    monkeypatch.setattr(
        mcp_server.httpx, "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.ASGITransport(app=app), **kwargs),
    )


async def test_status_success(runtime_transport, monkeypatch):
    import aion.runtime_status

    snapshot = {"ok": True, "source": "runtime_status", "fixture": False,
                "operations": {"arbitrary_terminal_commands_enabled": False}}
    monkeypatch.setattr(aion.runtime_status, "build_runtime_status", lambda: snapshot)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("runtime_status", {})
    assert not result.is_error
    assert result.structured_content == snapshot


async def test_status_policy_denied(runtime_transport, monkeypatch):
    import aion.main
    from fastapi import HTTPException

    def deny(authorization):
        raise HTTPException(status_code=403, detail="Invalid owner token")

    monkeypatch.setattr(aion.main, "_require_owner", deny)
    result = await mcp_server.mcp.call_tool("runtime_status", {})
    assert result.is_error
    assert "Policy denied" in result.content[0].text
    assert result.structured_content is None


async def test_status_missing_credentials(monkeypatch):
    monkeypatch.delenv("AION_OWNER_TOKEN", raising=False)
    result = await mcp_server.mcp.call_tool("runtime_status", {})
    assert result.is_error
    assert "Policy denied" in result.content[0].text


async def test_status_disconnected(monkeypatch):
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    original_client = httpx.AsyncClient

    def disconnected(request):
        raise httpx.ConnectError("private connection details", request=request)

    monkeypatch.setattr(
        mcp_server.httpx, "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(disconnected), **kwargs),
    )
    result = await mcp_server.mcp.call_tool("runtime_status", {})
    assert result.is_error
    assert result.content[0].text == "AION runtime is disconnected or unavailable."
    assert result.structured_content is None


async def test_only_read_only_status_is_exposed():
    tools = await mcp_server.mcp.list_tools()
    assert [tool.name for tool in tools] == ["runtime_status"]
    assert tools[0].annotations.read_only_hint is True
    assert tools[0].input_schema.get("properties", {}) == {}


@pytest.mark.parametrize("token,status", [(None, 401), ("wrong", 403), ("test-owner", 200)])
async def test_owner_status_policy(monkeypatch, token, status):
    import aion.runtime_status

    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    monkeypatch.setattr(aion.runtime_status, "build_runtime_status", lambda: {"ok": True})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await client.get("/owner/runtime/status", headers=headers)
    assert response.status_code == status
