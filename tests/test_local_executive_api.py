from __future__ import annotations

from fastapi.testclient import TestClient

from aion.main import app


client = TestClient(app, client=("127.0.0.1", 50000))


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

    response = client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["capability"] == "git.status"
    assert data["executor"] == "aion-local-controlled"
    assert data["arbitrary_commands_enabled"] is False


def test_rejects_arbitrary_command(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    response = client.post(
        "/local-executive/execute",
        json={"capability": "rm -rf /"},
    )

    assert response.status_code == 400


def test_rejects_caller_supplied_arguments(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    response = client.post(
        "/local-executive/execute",
        json={
            "capability": "git.status",
            "args": ["--whatever"],
        },
    )

    assert response.status_code == 422


def test_rejects_caller_supplied_command(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    response = client.post(
        "/local-executive/execute",
        json={
            "capability": "git.status",
            "command": "bash",
        },
    )

    assert response.status_code == 422


def test_local_executor_disabled_outside_local_mode(monkeypatch):
    monkeypatch.delenv("AION_RUNTIME_MODE", raising=False)

    response = client.post(
        "/local-executive/execute",
        json={"capability": "git.status"},
    )

    assert response.status_code == 503
