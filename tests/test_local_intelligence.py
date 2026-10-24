from __future__ import annotations

import io
import json

import aion.local_intelligence as local_intelligence


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_local_intelligence_skips_probe_outside_local_mode(monkeypatch):
    monkeypatch.delenv("AION_RUNTIME_MODE", raising=False)

    def fail_probe(*_args, **_kwargs):
        raise AssertionError("cloud/serverless status must not probe local Ollama")

    monkeypatch.setattr(local_intelligence, "_probe_models", fail_probe)

    status = local_intelligence.local_intelligence_status()

    assert status["enabled"] is False
    assert status["reachable"] is False
    assert status["actionable"] is False
    assert status["secret_required"] is False
    assert status["model"] == "aion:latest"


def test_local_intelligence_reports_installed_model(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")
    monkeypatch.setenv("AION_LOCAL_CONTEXT", "4096")

    monkeypatch.setattr(
        local_intelligence,
        "_probe_models",
        lambda _url: (True, ["aion:latest", "llama3.2:latest"], None),
    )

    status = local_intelligence.local_intelligence_status()

    assert status["enabled"] is True
    assert status["reachable"] is True
    assert status["model_installed"] is True
    assert status["actionable"] is True
    assert status["context"] == 4096
    assert status["endpoint"] == "http://127.0.0.1:11434"


def test_local_intelligence_fails_closed_when_model_missing(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_LOCAL_MODEL", "aion:latest")
    monkeypatch.setattr(
        local_intelligence,
        "_probe_models",
        lambda _url: (True, ["llama3.2:latest"], None),
    )

    status = local_intelligence.local_intelligence_status()

    assert status["reachable"] is True
    assert status["model_installed"] is False
    assert status["actionable"] is False


def test_local_context_invalid_value_falls_back(monkeypatch):
    monkeypatch.setenv("AION_LOCAL_CONTEXT", "not-a-number")
    assert local_intelligence.local_context_size() == 4096


def test_safe_endpoint_redacts_credentials_and_path():
    assert (
        local_intelligence._safe_endpoint("http://user:secret@example.test:11434/private?token=x")
        == "http://example.test:11434"
    )


def test_probe_models_reads_ollama_tags(monkeypatch):
    payload = {
        "models": [
            {"name": "aion:latest"},
            {"model": "llama3.2:latest"},
        ]
    }

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/tags"
        assert timeout == local_intelligence.STATUS_TIMEOUT_SECONDS
        return _Response(json.dumps(payload).encode())

    monkeypatch.setattr(local_intelligence, "urlopen", fake_urlopen)

    reachable, models, error = local_intelligence._probe_models("http://127.0.0.1:11434")

    assert reachable is True
    assert models == ["aion:latest", "llama3.2:latest"]
    assert error is None
