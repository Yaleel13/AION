from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

from aion.local_executor import (
    CAPABILITIES,
    Capability,
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


def test_media_capabilities_are_fixed_and_classified():
    audio = CAPABILITIES["media.audio.inputs"]
    camera = CAPABILITIES["media.camera.inputs"]
    runtime = CAPABILITIES["media.runtime"]
    listen = CAPABILITIES["media.voice.listen"]
    ask = CAPABILITIES["media.voice.ask"]

    assert audio.classification == "read"
    assert camera.classification == "read"
    assert runtime.classification == "read"
    assert listen.classification == "capture"
    assert ask.classification == "capture"
    assert audio.argv == (sys.executable, "-m", "aion.local_media", "audio")
    assert camera.argv == (sys.executable, "-m", "aion.local_media", "camera")
    assert runtime.argv == (sys.executable, "-m", "aion.local_media", "runtime")
    assert listen.argv == (sys.executable, "-m", "aion.local_voice")
    assert ask.argv == (sys.executable, "-m", "aion.local_voice_turn")


def test_unknown_command_cannot_be_executed(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    result = asyncio.run(execute_capability("rm -rf /"))

    assert result["ok"] is False
    assert result["error"] == "Unsupported local capability."


def test_git_status_executes_as_typed_capability(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    result = asyncio.run(execute_capability("git.status"))

    assert result["capability"] == "git.status"
    assert result["executor"] == "aion-local-controlled"
    assert result["arbitrary_commands_enabled"] is False
    assert result["sudo_enabled"] is False


def test_executor_uses_minimal_environment_and_hides_output(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "sentinel-owner-secret")
    script = (
        "import os, sys; "
        "print(os.getenv('AION_OWNER_TOKEN', 'absent')); "
        "sys.exit(0 if 'AION_OWNER_TOKEN' not in os.environ else 1)"
    )
    monkeypatch.setitem(
        CAPABILITIES,
        "test.environment",
        Capability("test.environment", (sys.executable, "-c", script), cwd=tmp_path),
    )

    result = asyncio.run(execute_capability("test.environment"))

    assert result["ok"] is True
    assert "sentinel-owner-secret" not in repr(result)
    assert "stdout" not in result
    assert "stderr" not in result


def test_executor_bounds_discarded_output(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    script = "import sys; sys.stdout.write('x' * 30000); sys.stderr.write('y' * 30000)"
    monkeypatch.setitem(
        CAPABILITIES,
        "test.output",
        Capability("test.output", (sys.executable, "-c", script), cwd=tmp_path),
    )

    result = asyncio.run(execute_capability("test.output"))

    assert result["ok"] is True
    assert result["output_truncated"] is True
    assert "stdout" not in result
    assert "stderr" not in result


def test_executor_redacts_startup_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setitem(
        CAPABILITIES,
        "test.startup",
        Capability("test.startup", (sys.executable, "-c", "pass"), cwd=tmp_path),
    )

    async def unavailable(*_args, **_kwargs):
        raise OSError("sentinel startup secret")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unavailable)
    result = asyncio.run(execute_capability("test.startup"))

    assert result["ok"] is False
    assert result["error"] == "Local capability is unavailable."
    assert "sentinel startup secret" not in repr(result)


def _wait_for_process_exit(pid: int) -> bool:
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


@pytest.mark.skipif(os.name != "posix", reason="process group cleanup is POSIX-specific")
def test_timeout_reaps_process_group_descendants(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    pid_file = tmp_path / "child.pid"
    script = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import sys, time; sys.stdout.write(\"x\" * 1000000); sys.stdout.flush(); time.sleep(60)']); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid)); "
        "time.sleep(60)"
    )
    monkeypatch.setitem(
        CAPABILITIES,
        "test.timeout",
        Capability("test.timeout", (sys.executable, "-c", script), timeout=1, cwd=tmp_path),
    )

    result = asyncio.run(execute_capability("test.timeout"))

    assert result["status"] == "timeout"
    assert pid_file.exists()
    assert _wait_for_process_exit(int(pid_file.read_text())) is True


@pytest.mark.skipif(os.name != "posix", reason="process group cleanup is POSIX-specific")
def test_cancellation_reaps_process_group_descendants(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    pid_file = tmp_path / "child.pid"
    script = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import sys, time; sys.stdout.write(\"x\" * 1000000); sys.stdout.flush(); time.sleep(60)']); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid)); "
        "time.sleep(60)"
    )
    monkeypatch.setitem(
        CAPABILITIES,
        "test.cancel",
        Capability("test.cancel", (sys.executable, "-c", script), timeout=30, cwd=tmp_path),
    )

    async def cancel() -> None:
        task = asyncio.create_task(execute_capability("test.cancel"))
        for _ in range(50):
            if pid_file.exists():
                break
            await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    assert pid_file.exists()
    assert _wait_for_process_exit(int(pid_file.read_text())) is True
