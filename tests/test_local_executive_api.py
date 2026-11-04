from __future__ import annotations

from fastapi.testclient import TestClient

from aion.main import app


client = TestClient(app, client=("127.0.0.1", 50000))
remote_client = TestClient(app, client=("192.0.2.1", 50000))


def test_capability_endpoint_lists_fixed_registry(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    response = client.get("/local-executive/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "local-controlled"
    assert data["arbitrary_commands_enabled"] is False

    names = {item["name"] for item in data["capabilities"]}
    assert "system.info" in names
    assert "git.status" in names
    assert "project.test" in names


def test_execute_typed_capability(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")

    response = client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
        headers={"Authorization": "Bearer owner-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["capability"] == "git.status"
    assert data["executor"] == "aion-local-controlled"
    assert data["arbitrary_commands_enabled"] is False


def test_rejects_arbitrary_command(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")

    response = client.post(
        "/local-executive/execute",
        json={"capability": "rm -rf /"},
        headers={"Authorization": "Bearer owner-token"},
    )

    assert response.status_code == 400


def test_rejects_caller_supplied_arguments(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")

    response = client.post(
        "/local-executive/execute",
        json={
            "capability": "git.status",
            "args": ["--whatever"],
        },
        headers={"Authorization": "Bearer owner-token"},
    )

    assert response.status_code == 422


def test_rejects_caller_supplied_command(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")

    response = client.post(
        "/local-executive/execute",
        json={
            "capability": "git.status",
            "command": "bash",
        },
        headers={"Authorization": "Bearer owner-token"},
    )

    assert response.status_code == 422


def test_rejects_caller_selected_execution_overrides(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")

    for field, value in {
        "path": "/tmp",
        "cwd": "/tmp",
        "environment": {"AION_OWNER_TOKEN": "override"},
        "timeout": 1,
    }.items():
        response = client.post(
            "/local-executive/execute",
            json={"capability": "git.status", field: value},
            headers={"Authorization": "Bearer owner-token"},
        )
        assert response.status_code == 422


def test_local_executor_disabled_outside_local_mode(monkeypatch):
    monkeypatch.delenv("AION_RUNTIME_MODE", raising=False)
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")

    response = client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
        headers={"Authorization": "Bearer owner-token"},
    )

    assert response.status_code == 503


def test_missing_or_wrong_owner_bearer_never_starts_a_process(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")
    started = False

    async def execute(_name: str):
        nonlocal started
        started = True
        return {}

    monkeypatch.setattr("aion.local_executor.execute_capability", execute)

    missing = client.post("/local-executive/execute", json={"capability": "git.status"})
    wrong = client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 403
    assert started is False


def test_agent_bearer_cannot_execute_owner_capability(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("AION_LOCAL_AGENT_TOKEN", "agent-token")

    response = client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
        headers={"Authorization": "Bearer agent-token"},
    )

    assert response.status_code == 403


def test_non_loopback_owner_request_never_starts_a_process(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")
    started = False

    async def execute(_name: str):
        nonlocal started
        started = True
        return {}

    monkeypatch.setattr("aion.local_executor.execute_capability", execute)
    response = remote_client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
        headers={"Authorization": "Bearer owner-token"},
    )

    assert response.status_code == 403
    assert started is False
