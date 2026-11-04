from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import httpx

from aion import main, owner_voice
from aion.main import app


def _tools() -> dict[str, str]:
    return {
        "ffmpeg": "/bin/ffmpeg",
        "whisper": "/bin/whisper",
        "piper": "/bin/piper",
        "ffplay": "/bin/ffplay",
        "source": "emeet-fixed-source",
        "model": "/models/whisper.bin",
        "voice": "/models/piper.onnx",
    }


def _process_running(pid: int) -> bool:
    try:
        return Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1].split()[0] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False


async def test_voice_turn_runs_fixed_flow_and_removes_temporary_media(monkeypatch):
    seen_paths: list[Path] = []
    monkeypatch.setattr(owner_voice, "_configured", lambda: (_tools(), None))
    monkeypatch.setattr(owner_voice, "_ollama_url", lambda: "http://127.0.0.1:11434")
    monkeypatch.setattr(owner_voice, "_model_ready", lambda *_args: asyncio.sleep(0, result=True))
    monkeypatch.setattr(owner_voice, "_reply", lambda *_args: asyncio.sleep(0, result="A brief local reply."))

    async def fixed_run(argv, _timeout):
        if argv[0] == "/bin/ffmpeg":
            path = Path(argv[-1])
            seen_paths.append(path)
            path.write_bytes(b"wav")
        elif argv[0] == "/bin/whisper":
            prefix = Path(argv[argv.index("-of") + 1])
            seen_paths.append(Path(f"{prefix}.txt"))
            Path(f"{prefix}.txt").write_text("Owner request.", encoding="utf-8")
        elif argv[0] == "/bin/piper":
            path = Path(argv[argv.index("-f") + 1])
            seen_paths.append(path)
            path.write_bytes(b"wav")
        return True

    monkeypatch.setattr(owner_voice, "_run", fixed_run)
    result = await owner_voice.run_owner_voice_turn()

    assert result["ok"] is True
    assert result["transcript"] == "Owner request."
    assert result["reply"] == "A brief local reply."
    assert result["durable_memory_written"] is False
    assert result["continuous_listening"] is False
    assert seen_paths and all(not path.exists() for path in seen_paths)


async def test_missing_prerequisite_never_starts_capture(monkeypatch):
    monkeypatch.setattr(owner_voice, "_configured", lambda: (None, "Voice is unavailable."))

    async def forbidden(*_args):
        pytest.fail("Voice capture started without prerequisites")

    monkeypatch.setattr(owner_voice, "_run", forbidden)
    assert await owner_voice.run_owner_voice_turn() == {
        "ok": False, "status": "unavailable", "error": "Voice is unavailable."
    }


async def test_model_unavailable_never_starts_capture(monkeypatch):
    monkeypatch.setattr(owner_voice, "_configured", lambda: (_tools(), None))
    monkeypatch.setattr(owner_voice, "_ollama_url", lambda: "http://127.0.0.1:11434")
    monkeypatch.setattr(owner_voice, "_model_ready", lambda *_args: asyncio.sleep(0, result=False))

    async def forbidden(*_args):
        pytest.fail("Voice capture started before model readiness")

    monkeypatch.setattr(owner_voice, "_run", forbidden)
    assert (await owner_voice.run_owner_voice_turn())["status"] == "unavailable"


async def test_oversized_ollama_responses_are_rejected():
    def oversized(_request):
        return httpx.Response(200, content=b"x" * (owner_voice.MAX_MODEL_RESPONSE_BYTES + 1))

    async with httpx.AsyncClient(transport=httpx.MockTransport(oversized)) as client:
        assert await owner_voice._model_ready(client, "http://127.0.0.1:11434", "aion:latest") is False
        assert await owner_voice._reply(client, "http://127.0.0.1:11434", "Owner request.") is None


@pytest.mark.parametrize(
    ("headers", "host", "body", "status"),
    [
        ({}, "127.0.0.1", {}, 401),
        ({"Authorization": "Bearer wrong"}, "127.0.0.1", {}, 403),
        ({"Authorization": "Bearer test-owner"}, "192.0.2.1", {}, 403),
        ({"Authorization": "Bearer test-owner"}, "127.0.0.1", {"device": "unsafe"}, 400),
    ],
)
async def test_voice_endpoint_denials_never_start_capture(monkeypatch, headers, host, body, status):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")

    async def forbidden(*_args, **_kwargs):
        pytest.fail("Denied voice request started a subprocess")

    monkeypatch.setattr(main, "_run_local_syntax_execution", forbidden)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(host, 123)),
        base_url="http://test",
    ) as client:
        response = await client.post("/owner/voice/turn", json=body, headers=headers)
    assert response.status_code == status


async def test_run_timeout_and_cancellation_reap_process_group(tmp_path):
    ready = tmp_path / "child.pid"
    script = (
        "import pathlib, subprocess, sys, time; "
        "child=subprocess.Popen([sys.executable,'-c','import os,time; os.write(1,b\"x\"*1000000); time.sleep(60)']); "
        f"pathlib.Path({str(ready)!r}).write_text(str(child.pid)); time.sleep(60)"
    )
    assert await owner_voice._run((__import__("sys").executable, "-c", script), 1) is False
    assert ready.exists()
    pid = int(ready.read_text())
    for _ in range(100):
        if not _process_running(pid):
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("Voice descendant process was not reaped")


async def test_run_cancellation_reaps_process_group(tmp_path):
    ready = tmp_path / "child.pid"
    script = (
        "import pathlib, subprocess, sys, time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        f"pathlib.Path({str(ready)!r}).write_text(str(child.pid)); time.sleep(60)"
    )
    task = asyncio.create_task(owner_voice._run((__import__("sys").executable, "-c", script), 30))
    for _ in range(100):
        if ready.exists():
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("Voice process did not start")
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    pid = int(ready.read_text())
    for _ in range(100):
        if not _process_running(pid):
            return
        await asyncio.sleep(0.01)
    pytest.fail("Cancelled voice descendant process was not reaped")
