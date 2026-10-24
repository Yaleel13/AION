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


def test_reasoning_posts_history_to_loopback_ollama(monkeypatch):
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

    history = [
        {"role": "user", "content": "Remember our last turn."},
        {"role": "assistant", "content": "I remember it."},
    ]
    result = local_voice_turn.reason_locally("Can you hear me?", history)

    assert result["ok"] is True
    assert result["reply"] == "I hear you."
    assert result["history_messages"] == 2
    assert result["network_required"] is False
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["payload"]["model"] == "aion:latest"
    assert seen["payload"]["messages"][1:3] == history
    assert seen["payload"]["messages"][-1]["content"] == "Can you hear me?"
    assert seen["payload"]["stream"] is False


def test_voice_memory_load_is_bounded(monkeypatch):
    messages = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"message-{index}"}
        for index in range(20)
    ]

    monkeypatch.setattr(
        local_voice_turn,
        "handle_local_memory",
        lambda _request: {"found": True, "messages": messages},
    )

    history, error = local_voice_turn._load_voice_history()

    assert error is None
    assert len(history) == local_voice_turn.VOICE_HISTORY_LIMIT
    assert history[0]["content"] == "message-8"
    assert history[-1]["content"] == "message-19"


def test_voice_memory_append_uses_stable_session(monkeypatch):
    seen = {}

    def fake_memory(request):
        seen["request"] = request
        return {"saved": True, "message_count": 2}

    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")
    monkeypatch.setattr(local_voice_turn, "handle_local_memory", fake_memory)

    saved, error = local_voice_turn._save_voice_turn("Hello AION", "I hear you.")

    assert saved is True
    assert error is None
    request = seen["request"]
    assert request.action == "append"
    assert request.client_session_id == "aion-local-voice-primary"
    assert [message.role for message in request.messages] == ["user", "assistant"]
    assert [message.content for message in request.messages] == ["Hello AION", "I hear you."]
    assert request.model == "aion:latest"
    assert request.runtime == "ollama-local-voice"


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


def test_voice_turn_runs_memory_listen_reason_speak_and_play(monkeypatch, tmp_path):
    wav = tmp_path / "reply.wav"
    wav.write_bytes(b"RIFF")

    monkeypatch.setattr(
        local_voice_turn,
        "listen_once",
        lambda: {"ok": True, "kind": "voice-listen", "transcript": "AION, can you hear me?"},
    )
    monkeypatch.setattr(
        local_voice_turn,
        "_load_voice_history",
        lambda: ([{"role": "assistant", "content": "Previous reply."}], None),
    )

    seen = {}

    def fake_reason(text, history):
        seen["reason_text"] = text
        seen["history"] = history
        return {"ok": True, "reply": "Yes. I can hear you.", "model": "aion:latest"}

    monkeypatch.setattr(local_voice_turn, "reason_locally", fake_reason)
    monkeypatch.setattr(
        local_voice_turn,
        "_save_voice_turn",
        lambda transcript, reply: (
            seen.update({"saved_transcript": transcript, "saved_reply": reply}) or True,
            None,
        ),
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
    assert result["memory_session_id"] == "aion-local-voice-primary"
    assert result["history_messages"] == 1
    assert result["memory_saved"] is True
    assert result["played"] is True
    assert result["network_required"] is False
    assert result["continuous_listening"] is False
    assert seen["history"] == [{"role": "assistant", "content": "Previous reply."}]
    assert seen["saved_transcript"] == "AION, can you hear me?"
    assert seen["saved_reply"] == "Yes. I can hear you."
