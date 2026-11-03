"""Exercise MCP dispatch and the real HTTP owner policy without a live service."""

import json

import httpx
import pytest
from mcp import Client

from aion import mcp_server
from aion.main import app
from tests.test_capability_audit import audit_store


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

    def forbidden(*args, **kwargs):
        pytest.fail("Missing credentials reached HTTP transport")

    monkeypatch.setattr(mcp_server.httpx, "AsyncClient", forbidden)
    result = await mcp_server.mcp.call_tool("runtime_status", {})
    assert result.is_error
    assert "Policy denied" in result.content[0].text


async def test_status_catalog_denial_never_builds_status(runtime_transport, monkeypatch):
    from aion import capabilities
    import aion.runtime_status

    catalog = capabilities.capability_catalog()
    catalog["capabilities"]["runtime_status"]["read"] = False
    monkeypatch.setattr(capabilities, "capability_catalog", lambda: catalog)

    def forbidden():
        pytest.fail("Denied MCP capability reached its status handler")

    monkeypatch.setattr(aion.runtime_status, "build_runtime_status", forbidden)
    result = await mcp_server.mcp.call_tool("runtime_status", {})
    assert result.is_error
    assert "Policy denied" in result.content[0].text
    assert result.structured_content is None


async def test_status_policy_evaluation_failure_is_a_structured_denial(runtime_transport, monkeypatch):
    from aion import capabilities
    import aion.runtime_status

    def failed_policy():
        raise RuntimeError("private policy details")

    def forbidden():
        pytest.fail("Failed policy reached status handler")

    monkeypatch.setattr(capabilities, "capability_catalog", failed_policy)
    monkeypatch.setattr(aion.runtime_status, "build_runtime_status", forbidden)
    result = await mcp_server.mcp.call_tool("runtime_status", {})
    assert result.is_error
    assert result.structured_content is None
    assert "Policy denied" in result.content[0].text
    assert "private" not in result.content[0].text


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
    assert result.meta is None


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


async def test_sdk_metadata_correlates_with_runtime_audit(runtime_transport, audit_store, monkeypatch):
    import aion.runtime_status

    snapshot = {"ok": True, "source": "runtime_status", "fixture": False}
    monkeypatch.setattr(aion.runtime_status, "build_runtime_status", lambda: snapshot)
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("runtime_status", {})
    assert result.structured_content == snapshot
    assert result.meta and set(result.meta) - {"io.modelcontextprotocol/serverInfo"} == {"aion/request_id"}
    request_id = result.meta["aion/request_id"]
    rows = audit_store.list_audit()
    assert len(rows) == 2
    assert all(row["detail"]["request_id"] == request_id for row in rows)
    assert rows[0]["detail"]["outcome"] == "succeeded"


@pytest.mark.parametrize("status", [200, 403, 500])
@pytest.mark.parametrize("request_id", ["a" * 32, "A" * 32, "a" * 31, "a" * 33, "z" * 32, None, "", "a" * 32 + ", " + "b" * 32])
async def test_only_valid_correlation_enters_mcp_metadata(status, request_id, monkeypatch):
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    original_client = httpx.AsyncClient
    snapshot = {"ok": True, "source": "runtime_status"}

    def upstream(request):
        headers = {"Authorization": "Bearer test-owner", "X-Internal-Debug": "private details"}
        if request_id is not None:
            headers["X-AION-Request-ID"] = request_id
        return httpx.Response(status, json=snapshot, headers=headers)

    monkeypatch.setattr(mcp_server.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(upstream), **kwargs))
    async with Client(mcp_server.mcp) as client:
        result = await client.call_tool("runtime_status", {})
    assert result.is_error is (status != 200)
    metadata = {key: value for key, value in (result.meta or {}).items() if key != "io.modelcontextprotocol/serverInfo"}
    assert metadata == ({"aion/request_id": request_id} if request_id == "a" * 32 else {})
    assert result.structured_content == (snapshot if status == 200 else None)
    if status == 200:
        assert json.loads(result.content[0].text) == snapshot
    else:
        assert result.content[0].text == (
            "Policy denied: runtime owner authorization unavailable or rejected." if status == 403
            else "AION runtime is disconnected or unavailable."
        )
    assert "aion/request_id" not in result.content[0].text
    if request_id == "a" * 32:
        assert result.model_dump(by_alias=True)["_meta"]["aion/request_id"] == request_id
        assert request_id not in result.content[0].text
    serialized = result.model_dump_json()
    assert "test-owner" not in serialized
    assert "private details" not in serialized
