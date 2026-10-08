from __future__ import annotations

from aion.local_executor import (
    CAPABILITIES,
    execute_capability,
    executor_status,
)


def test_local_executor_requires_local_mode(monkeypatch):
    monkeypatch.delenv("AION_RUNTIME_MODE", raising=False)

    status = executor_status()

    assert status["connected"] is False
    assert status["mode"] is None
    assert status["arbitrary_commands_enabled"] is False
    assert status["sudo_enabled"] is False


def test_local_executor_connects_in_local_mode(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    status = executor_status()

    assert status["connected"] is True
    assert status["mode"] == "local-controlled"
    assert status["arbitrary_commands_enabled"] is False
    assert status["sudo_enabled"] is False


def test_capability_registry_contains_no_sudo_or_shell():
    for capability in CAPABILITIES.values():
        assert capability.argv
        assert capability.argv[0] not in {"sudo", "su", "sh", "bash", "zsh"}


def test_unknown_command_cannot_be_executed(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    result = execute_capability("rm -rf /")

    assert result["ok"] is False
    assert result["error"] == "Unsupported local capability."


def test_git_status_executes_as_typed_capability(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    result = execute_capability("git.status")

    assert result["capability"] == "git.status"
    assert result["executor"] == "aion-local-controlled"
    assert result["arbitrary_commands_enabled"] is False
    assert result["sudo_enabled"] is False
