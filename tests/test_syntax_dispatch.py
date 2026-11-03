"""The existing validator launches only after transport and capability gates."""

import asyncio
import os

import httpx
import pytest

from aion import capabilities, local_validation
from aion.main import app
from fastapi import HTTPException, Request

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Validation is POSIX-only")


@pytest.fixture(autouse=True)
def local_owner(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")


@pytest.mark.parametrize("failure,status", [("disabled", 403), ("unconfigured", 403),
                                            ("missing", 403), ("malformed", 403),
                                            ("exception", 503), ("invalid_policy", 503)])
async def test_capability_denial_or_policy_failure_starts_zero_processes(failure, status, monkeypatch):
    catalog = capabilities.capability_catalog()
    entry = catalog["capabilities"]["runtime.syntax"]
    if failure == "disabled":
        entry["execute"] = False
    elif failure == "unconfigured":
        entry["configured"] = False
    elif failure == "missing":
        del catalog["capabilities"]["runtime.syntax"]
    elif failure == "malformed":
        entry["execute"] = "true"
    attempts = []

    def policy():
        if failure == "exception":
            raise RuntimeError("private policy details")
        return None if failure == "invalid_policy" else catalog

    async def forbidden(*args, **kwargs):
        attempts.append(True)
        pytest.fail("Policy-denied validation attempted process creation")

    monkeypatch.setattr(capabilities, "capability_catalog", policy)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://test") as client:
        response = await client.post("/local-executive/validate", json={}, headers={"Authorization": "Bearer test-owner"})
    assert response.status_code == status
    assert attempts == []
    assert "private" not in response.text


async def test_authorized_http_request_checks_policy_and_starts_exactly_one_job(monkeypatch):
    native_spawn = asyncio.create_subprocess_exec
    catalog = capabilities.capability_catalog()
    events = []

    def policy():
        events.append("policy")
        return catalog

    async def spawn(*args, **kwargs):
        events.append("spawn")
        assert args == local_validation.ARGV
        assert kwargs["env"] == local_validation.JOB_ENV
        assert kwargs["cwd"] == local_validation.PROJECT_ROOT
        return await native_spawn(*args, **kwargs)

    monkeypatch.setattr(capabilities, "capability_catalog", policy)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://test") as client:
        response = await client.post("/local-executive/validate", json={}, headers={"Authorization": "Bearer test-owner"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"ok", "job", "status", "exit_code", "output", "truncated", "arbitrary_commands_enabled"}
    assert data["ok"] is True
    assert data["job"] == "runtime.syntax"
    assert data["status"] == "succeeded"
    assert data["arbitrary_commands_enabled"] is False
    assert len(data["output"].encode()) <= local_validation.MAX_OUTPUT_BYTES
    assert events == ["policy", "spawn"]


async def test_async_dispatch_preserves_the_handler_result(monkeypatch):
    snapshot = {"ok": True, "job": "runtime.syntax", "status": "succeeded"}
    calls = []

    async def handler():
        calls.append(True)
        return snapshot

    monkeypatch.setattr(local_validation, "run_validation", handler)
    result = await capabilities.dispatch_capability_async("runtime.syntax", action="execute")
    assert result is snapshot
    assert calls == [True]


def test_sync_dispatch_cannot_launch_an_async_job(monkeypatch):
    calls = []

    async def handler():
        calls.append(True)
        pytest.fail("Synchronous dispatch invoked validation")

    monkeypatch.setattr(local_validation, "run_validation", handler)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime.syntax", action="execute")
    assert error.value.code == "policy_denied"
    assert calls == []


@pytest.mark.parametrize("action", ["read", "propose", "approve", "configured"])
async def test_syntax_requires_execute_action_before_policy(action, monkeypatch):
    def forbidden():
        pytest.fail("Wrong action reached policy")

    monkeypatch.setattr(capabilities, "capability_catalog", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        await capabilities.dispatch_capability_async("runtime.syntax", action=action)
    assert error.value.code == "policy_denied"


@pytest.mark.parametrize("mode,owner,configured,execute", [("cloud", True, False, False),
                                                          ("local", False, True, False),
                                                          ("local", True, True, True)])
def test_live_syntax_permissions_reflect_existing_runtime_gates(mode, owner, configured, execute, monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", mode)
    snapshot = {
        "storage": {"configured": True},
        "operations": {"owner_token_configured": owner, "terminal_executor_connected": False},
        "moltbook": {"configured": False, "outbound_enabled": False, "execute_enabled": False},
    }
    monkeypatch.setattr(capabilities, "build_runtime_status", lambda: snapshot)
    entry = capabilities.capability_registry()["capabilities"]["runtime.syntax"]
    assert entry["configured"] is configured
    assert entry["execute"] is execute
    assert entry["read"] is entry["propose"] is entry["approve"] is False


async def test_transport_auth_denies_before_capability_policy(monkeypatch):
    def forbidden():
        pytest.fail("Unauthorized request reached capability policy")

    monkeypatch.setattr(capabilities, "capability_catalog", forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/local-executive/validate", json={})
    assert response.status_code == 401


@pytest.mark.parametrize("outcome", ["success", "denied", "policy_failure"])
async def test_immediate_completion_drains_watcher_even_if_poll_consumes_cancellation(outcome, monkeypatch):
    from aion.main import LocalValidationRequest, local_executive_validate

    tasks = []
    native_create_task = asyncio.create_task

    def create_task(coro, *args, **kwargs):
        task = native_create_task(coro, *args, **kwargs)
        if coro.__qualname__.endswith("watch_disconnect") or coro.__qualname__ == "dispatch_capability_async":
            tasks.append(task)
        return task

    async def poll():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            return False  # Model the receive poll consuming endpoint cancellation.

    async def handler():
        return {"ok": True}

    catalog = capabilities.capability_catalog()
    catalog["capabilities"]["runtime.syntax"]["execute"] = outcome != "denied"

    def policy():
        if outcome == "policy_failure":
            raise RuntimeError("private policy details")
        return catalog

    async def forbidden(*args, **kwargs):
        pytest.fail("Lifecycle-only test attempted process creation")

    request = Request({"type": "http", "client": ("127.0.0.1", 123), "headers": [], "query_string": b""})
    monkeypatch.setattr(request, "is_disconnected", poll)
    monkeypatch.setattr(capabilities, "capability_catalog", policy)
    monkeypatch.setattr(local_validation, "run_validation", handler)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    monkeypatch.setattr(asyncio, "create_task", create_task)
    call = local_executive_validate(LocalValidationRequest(), request, "Bearer test-owner")
    if outcome == "success":
        assert await asyncio.wait_for(call, 2) == {"ok": True}
    else:
        with pytest.raises(HTTPException) as error:
            await asyncio.wait_for(call, 2)
        assert error.value.status_code == (403 if outcome == "denied" else 503)
    assert len(tasks) == 2
    assert all(task.done() for task in tasks)
