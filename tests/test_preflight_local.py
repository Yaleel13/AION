from __future__ import annotations

import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "preflight_local", Path(__file__).parents[1] / "scripts/preflight_local.py"
)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def _ready(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "AION_RUNTIME_MODE=local\nAION_OWNER_TOKEN=secret-owner-token\nAION_AUDIO_CAPTURE_ENABLED=true\n"
    )
    (tmp_path / ".env.local").write_text("AION_OWNER_TOKEN=secret-owner-token\n")
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "node_modules").mkdir()
    python = tmp_path / "python"
    python.write_text("")
    monkeypatch.setattr(preflight, "VENV_PYTHON", python)
    monkeypatch.setattr(preflight, "REQUIRED_NODE_FILES", ("package.json", "node_modules"))
    monkeypatch.setattr(preflight, "VOICE_FILES", ())
    monkeypatch.setattr(preflight, "_port_occupant", lambda _port: "available")
    monkeypatch.setattr(preflight, "_ollama_models", lambda: {"aion:latest"})
    monkeypatch.setattr(preflight, "_emeet_source", lambda: True)
    monkeypatch.setattr(preflight.shutil, "which", lambda name: "/bin/tool" if name in {"node", "piper"} else None)
    monkeypatch.setattr(preflight.subprocess, "run", lambda *_a, **_kw: type("R", (), {"returncode": 0})())


def _status(report, name):
    return next(item["status"] for item in report["checks"] if item["name"] == name)


def test_preflight_hides_secret_values(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    report = preflight.collect(tmp_path)
    assert _status(report, "runtime-configuration") == "ok"
    assert "secret-owner-token" not in repr(report)
    assert report["local_ready"] is True
    assert report["voice_ready"] is False


def test_preflight_reports_missing_dependencies(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr(preflight, "VENV_PYTHON", tmp_path / "missing-python")
    monkeypatch.setattr(preflight.shutil, "which", lambda _name: None)
    report = preflight.collect(tmp_path)
    assert _status(report, "python-venv") == "missing"
    assert _status(report, "node-dependencies") == "missing"
    assert _status(report, "voice-prerequisites") == "incomplete"


def test_preflight_reports_occupied_ports(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr(preflight, "_port_occupant", lambda port: "unknown" if port == 8000 else "available")
    report = preflight.collect(tmp_path)
    assert _status(report, "runtime-port") == "occupied-unknown"
    assert report["local_ready"] is False


def test_preflight_identifies_runtime_health_without_probing_unknown_listeners(monkeypatch):
    monkeypatch.setattr(preflight, "_port_available", lambda _port: False)
    monkeypatch.setattr(
        preflight,
        "_loopback_json",
        lambda url, timeout: {"status": "ok", "runtime": "agent-v1"} if url.endswith("/health") else None,
    )
    assert preflight._port_occupant(8000) == "aion"
    assert preflight._port_occupant(3000) == "unknown"


def test_preflight_reports_ollama_and_emeet_absence(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr(preflight, "_ollama_models", lambda: None)
    monkeypatch.setattr(preflight, "_emeet_source", lambda: False)
    report = preflight.collect(tmp_path)
    assert _status(report, "ollama") == "unavailable"
    assert _status(report, "emeet-input") == "unavailable"


def test_preflight_reports_missing_piper(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    monkeypatch.setattr(preflight.shutil, "which", lambda name: "/bin/node" if name == "node" else None)
    report = preflight.collect(tmp_path)
    assert _status(report, "voice-prerequisites") == "incomplete"


def test_preflight_handles_unreadable_or_malformed_configuration(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    (tmp_path / ".env").write_text("AION_OWNER_TOKEN='secret-owner-token\n")
    report = preflight.collect(tmp_path)
    assert _status(report, "runtime-configuration") == "incomplete"
    assert "secret-owner-token" not in repr(report)


def test_preflight_handles_inaccessible_configuration(monkeypatch, tmp_path):
    config = tmp_path / ".env"
    config.write_text("AION_OWNER_TOKEN=secret-owner-token\n")
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError()))
    assert preflight._config(config) == ({}, "unreadable")


def test_loopback_json_rejects_non_loopback_urls(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "build_opener",
        lambda *_args: (_ for _ in ()).throw(AssertionError("network call")),
    )
    assert preflight._loopback_json("http://example.test/api/tags", timeout=1) is None
