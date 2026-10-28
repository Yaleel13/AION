from __future__ import annotations

import io
import json

from aion import local_voice_turn


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_voice_model_env_overrides_main_local_model(monkeypatch):
    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")
    monkeypatch.setenv("AION_VOICE_MODEL", "llama3.2:1b-instruct-q4_K_M")

    assert local_voice_turn._voice_model_name() == "llama3.2:1b-instruct-q4_K_M"


def test_voice_model_falls_back_to_main_local_model(monkeypatch):
    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")
    monkeypatch.delenv("AION_VOICE_MODEL", raising=False)

    assert local_voice_turn._voice_model_name() == "aion:latest"


def test_truth_guard_replaces_unverified_execution_claim():
    reply, triggered = local_voice_turn._apply_truth_guard(
        "I've been running some diagnostics on our system's performance."
    )

    assert triggered is True
    assert "haven't checked" in reply
    assert "controlled actions" in reply


def test_truth_guard_preserves_non_execution_reply():
    reply, triggered = local_voice_turn._apply_truth_guard(
        "I suggest we focus on voice latency next."
    )

    assert triggered is False
    assert reply == "I suggest we focus on voice latency next."


def test_reasoning_uses_dedicated_voice_model(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OLLAMA_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")
    monkeypatch.setenv("AION_VOICE_MODEL", "llama3.2:1b-instruct-q4_K_M")

    seen = {}

    def fake_urlopen(request, timeout):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(
            json.dumps({"message": {"content": "I suggest we focus on voice latency next."}}).encode("utf-8")
        )

    monkeypatch.setattr(local_voice_turn, "urlopen", fake_urlopen)

    result = local_voice_turn.reason_locally("Help me think through the voice latency tradeoffs.", [])

    assert result["ok"] is True
    assert result["model"] == "llama3.2:1b-instruct-q4_K_M"
    assert seen["payload"]["model"] == "llama3.2:1b-instruct-q4_K_M"
