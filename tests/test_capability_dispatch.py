"""Capability policy gates precede handler work on the shared status path."""

import httpx
import pytest

from aion import capabilities, runtime_status
from aion.main import app


def forbidden(*args, **kwargs):
    pytest.fail("Denied capability reached handler work")


def test_authorized_dispatch_returns_the_original_status_payload(monkeypatch):
    snapshot = {"ok": True, "source": "runtime_status", "fixture": False}
    calls = []

    def status():
        calls.append(True)
        return snapshot

    monkeypatch.setattr(runtime_status, "build_runtime_status", status)
    monkeypatch.setattr(capabilities, "capability_registry", forbidden)
    assert capabilities.dispatch_capability("runtime_status") is snapshot
    assert calls == [True]


@pytest.mark.parametrize("name", ["unknown", "runtime.syntax", "terminal", "system.info", "shell"])
def test_unknown_or_unregistered_capabilities_do_not_reach_policy_or_handler(name, monkeypatch):
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    monkeypatch.setattr(capabilities, "capability_catalog", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability(name)
    assert error.value.code == "unknown_capability"


@pytest.mark.parametrize("entry", [None, {"configured": False, "read": True},
                                  {"configured": True, "read": False},
                                  {"configured": True, "read": "true"}])
def test_denied_or_missing_permissions_never_reach_handler(entry, monkeypatch):
    catalog = {"capabilities": {"runtime_status": entry} if entry else {}}
    monkeypatch.setattr(capabilities, "capability_catalog", lambda: catalog)
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime_status")
    assert error.value.code == "policy_denied"


@pytest.mark.parametrize("action", ["execute", "approve", "propose", "configured", "unknown"])
def test_status_handler_cannot_be_used_for_other_actions(action, monkeypatch):
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    monkeypatch.setattr(capabilities, "capability_catalog", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime_status", action=action)
    assert error.value.code == "policy_denied"


@pytest.mark.parametrize("catalog", [None, {}, [], {"capabilities": None}, {"capabilities": []}])
def test_invalid_policy_structure_fails_closed(catalog, monkeypatch):
    monkeypatch.setattr(capabilities, "capability_catalog", lambda: catalog)
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime_status")
    assert error.value.code == "policy_unavailable"
    assert str(error.value) == "Capability policy is unavailable."


@pytest.mark.parametrize("entry", [None, [], "read", {"configured": 1, "read": True}])
def test_malformed_permission_entry_never_invokes_handler(entry, monkeypatch):
    monkeypatch.setattr(capabilities, "capability_catalog", lambda: {"capabilities": {"runtime_status": entry}})
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime_status")
    assert error.value.code == "policy_denied"


def test_permission_evaluation_failure_is_closed_and_redacted(monkeypatch):
    class BrokenEntry(dict):
        def get(self, key, default=None):
            raise RuntimeError("private policy details")

    monkeypatch.setattr(capabilities, "capability_catalog", lambda: {"capabilities": {"runtime_status": BrokenEntry()}})
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime_status")
    assert error.value.code == "policy_unavailable"
    assert "private" not in str(error.value)


def test_resolution_precedes_policy_and_policy_precedes_handler(monkeypatch):
    events = []
    catalog = capabilities.capability_catalog()

    def policy():
        events.append("policy")
        return catalog

    def status():
        events.append("handler")
        return {"ok": True}

    monkeypatch.setattr(capabilities, "capability_catalog", policy)
    monkeypatch.setattr(runtime_status, "build_runtime_status", status)
    for name, action in [("unknown", "read"), ("runtime_status", "execute")]:
        with pytest.raises(capabilities.CapabilityDispatchError):
            capabilities.dispatch_capability(name, action=action)
        assert events == []
    assert capabilities.dispatch_capability("runtime_status") == {"ok": True}
    assert events == ["policy", "handler"]


def test_handler_failure_is_not_misclassified_as_policy_failure(monkeypatch):
    def unavailable():
        raise RuntimeError("handler unavailable")

    monkeypatch.setattr(runtime_status, "build_runtime_status", unavailable)
    with pytest.raises(RuntimeError, match="handler unavailable") as error:
        capabilities.dispatch_capability("runtime_status")
    assert not isinstance(error.value, capabilities.CapabilityDispatchError)


@pytest.mark.parametrize("provided,configured,status,detail", [(None, True, 401, "Missing bearer token"), ("wrong", True, 403, "Invalid owner token"), (None, False, 503, "AION_OWNER_TOKEN is not configured")])
async def test_owner_policy_denies_before_dispatch(provided, configured, status, detail, monkeypatch):
    if configured:
        monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    else:
        monkeypatch.delenv("AION_OWNER_TOKEN", raising=False)
    monkeypatch.setattr(capabilities, "dispatch_capability", forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {provided}"} if provided else {}
        response = await client.get("/owner/runtime/status", headers=headers)
    assert response.status_code == status
    assert response.json() == {"detail": detail}


async def test_public_status_remains_public_without_owner_configuration(monkeypatch):
    monkeypatch.delenv("AION_OWNER_TOKEN", raising=False)
    snapshot = {"ok": True, "source": "runtime_status", "fixture": False}
    monkeypatch.setattr(runtime_status, "build_runtime_status", lambda: snapshot)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/runtime/status")
    assert response.status_code == 200
    assert response.json() == snapshot


@pytest.mark.parametrize("path", ["/runtime/status", "/owner/runtime/status"])
async def test_policy_evaluation_errors_are_safe_and_do_not_reach_handler(path, monkeypatch):
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")

    def failed_policy():
        raise RuntimeError("private policy configuration details")

    monkeypatch.setattr(capabilities, "capability_catalog", failed_policy)
    monkeypatch.setattr(runtime_status, "build_runtime_status", forbidden)
    with pytest.raises(capabilities.CapabilityDispatchError) as error:
        capabilities.dispatch_capability("runtime_status")
    assert error.value.code == "policy_unavailable"
    assert "private" not in str(error.value)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path, headers={"Authorization": "Bearer test-owner"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Capability policy is unavailable."}


async def test_both_http_routes_share_the_capability_dispatcher(monkeypatch):
    calls = []
    snapshot = {"ok": True, "source": "runtime_status", "fixture": False}

    def dispatch(name):
        calls.append(name)
        return snapshot

    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")
    monkeypatch.setattr(capabilities, "dispatch_capability", dispatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        public = await client.get("/runtime/status")
        owner = await client.get("/owner/runtime/status", headers={"Authorization": "Bearer test-owner"})
    assert public.status_code == owner.status_code == 200
    assert public.json() == owner.json() == snapshot
    assert calls == ["runtime_status", "runtime_status"]
