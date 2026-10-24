from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

from aion import local_voice_turn


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_reasoning_rejects_non_loopback_ollama(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OLLAMA_URL", "https://example.com")

    result = local_voice_turn.reason_locally("hello")

    assert result["ok"] is False
    assert "loopback" in result["error"].lower()


def test_reasoning_posts_to_loopback_ollama(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OLLAMA_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")

    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(json.dumps({"message": {"content": "I hear you."}}).encode("utf-8"))

    monkeypatch.setattr(local_voice_turn, "urlopen", fake_urlopen)

    result = local_voice_turn.reason_locally("Can you hear me?")

    assert result["ok"] is True
    assert result["reply"] == "I hear you."
    assert result["network_required"] is False
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["payload"]["model"] == "aion:latest"
    assert seen["payload"]["messages"][-1]["content"] == "Can you hear me?"
    assert seen["payload"]["stream"] is False


def test_synthesize_requires_voice_model(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_PIPER_VOICE", str(tmp_path / "missing.onnx"))
    monkeypatch.setattr(local_voice_turn.shutil, "which", lambda name: "/usr/bin/piper" if name == "piper" else None)

    result = local_voice_turn.synthesize_reply("hello")

    assert result["ok"] is False
    assert "missing" in result["error"].lower()


def test_synthesize_uses_fixed_piper_shape(monkeypatch, tmp_path):
    voice = tmp_path / "voice.onnx"
    voice.write_bytes(b"model")
    Path(f"{voice}.json").write_text("{}", encoding="utf-8")
    media_root = tmp_path / "media"
    media_root.mkdir()

    monkeypatch.setenv("AION_PIPER_VOICE", str(voice))
    monkeypatch.setattr(local_voice_turn, "_media_root", lambda: media_root)
    monkeypatch.setattr(local_voice_turn.shutil, "which", lambda name: "/usr/bin/piper" if name == "piper" else None)

    seen = None

    def fake_run(argv, **_kwargs):
        nonlocal seen
        seen = tuple(argv)
        output = media_root / "latest-aion-reply.wav"
        output.write_bytes(b"RIFF-voice")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(local_voice_turn.subprocess, "run", fake_run)

    result = local_voice_turn.synthesize_reply("AION online.")

    assert result["ok"] is True
    assert seen == (
        "/usr/bin/piper",
        "-m",
        str(voice),
        "-f",
        str(media_root / "latest-aion-reply.wav"),
        "--",
        "AION online.",
    )


def test_voice_turn_runs_listen_reason_speak_and_play(monkeypatch, tmp_path):
    wav = tmp_path / "reply.wav"
    wav.write_bytes(b"RIFF")

    monkeypatch.setattr(
        local_voice_turn,
        "listen_once",
        lambda: {"ok": True, "kind": "voice-listen", "transcript": "AION, can you hear me?"},
    )
    monkeypatch.setattr(
        local_voice_turn,
        "reason_locally",
        lambda text: {"ok": True, "reply": "Yes. I can hear you.", "model": "aion:latest"},
    )
    monkeypatch.setattr(
        local_voice_turn,
        "synthesize_reply",
        lambda text: {"ok": True, "voice": "/voices/ryan.onnx", "path": str(wav)},
    )
    monkeypatch.setattr(
        local_voice_turn,
        "play_reply",
        lambda path: {"ok": True, "played": True, "error": None},
    )

    result = local_voice_turn.voice_turn()

    assert result["ok"] is True
    assert result["kind"] == "voice-turn"
    assert result["transcript"] == "AION, can you hear me?"
    assert result["reply"] == "Yes. I can hear you."
    assert result["reasoning_model"] == "aion:latest"
    assert result["played"] is True
    assert result["network_required"] is False
    assert result["continuous_listening"] is False
