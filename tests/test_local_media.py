from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from aion import local_media


def test_camera_inventory_is_read_only(monkeypatch, tmp_path):
    fake_sysfs = tmp_path / "video4linux"
    video0 = fake_sysfs / "video0"
    video0.mkdir(parents=True)
    (video0 / "name").write_text("Test Camera\n", encoding="utf-8")

    real_glob = Path.glob

    def fake_glob(self: Path, pattern: str):
        if str(self) == "/sys/class/video4linux" and pattern == "video*":
            return iter([video0])
        return real_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", fake_glob)

    data = local_media.camera_inventory()

    assert data["kind"] == "camera"
    assert data["capture_enabled"] is False
    assert data["count"] == 1
    assert data["devices"][0]["name"] == "Test Camera"


def test_audio_inventory_reports_sources_without_capture(monkeypatch):
    monkeypatch.delenv("AION_AUDIO_CAPTURE_ENABLED", raising=False)
    monkeypatch.setattr(
        local_media,
        "_pactl_sources",
        lambda: ([{"id": "1", "name": "test-source"}], None),
    )
    monkeypatch.setattr(local_media.shutil, "which", lambda _name: None)

    data = local_media.audio_inventory()

    assert data["kind"] == "audio-input"
    assert data["capture_enabled"] is False
    assert data["count"] == 1
    assert data["sources"][0]["name"] == "test-source"


def test_runtime_inventory_reports_local_voice_components(monkeypatch, tmp_path):
    model = tmp_path / "ggml-base.en.bin"
    model.write_bytes(b"model")
    monkeypatch.setenv("AION_WHISPER_MODEL", str(model))
    monkeypatch.setattr(
        local_media.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"ffmpeg", "pactl", "whisper-cli", "piper"} else None,
    )
    monkeypatch.setattr(
        local_media.importlib.util,
        "find_spec",
        lambda name: object() if name == "vosk" else None,
    )

    data = local_media.runtime_inventory()

    assert data["kind"] == "media-runtime"
    assert data["network_required"] is False
    assert data["tools"]["ffmpeg"] == "/usr/bin/ffmpeg"
    assert data["tools"]["pactl"] == "/usr/bin/pactl"
    assert data["tools"]["whisper-cli"] == "/usr/bin/whisper-cli"
    assert data["tools"]["piper"] == "/usr/bin/piper"
    assert data["python_modules"]["vosk"] is True
    assert data["python_modules"]["faster_whisper"] is False
    assert data["whisper_model_present"] is True


def test_audio_capture_fails_closed_without_owner_gate(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.delenv("AION_AUDIO_CAPTURE_ENABLED", raising=False)

    called = False

    def should_not_run(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess must not run while capture is disabled")

    monkeypatch.setattr(local_media.subprocess, "run", should_not_run)

    data = local_media.capture_emeet_audio()

    assert data["ok"] is False
    assert data["capture_enabled"] is False
    assert "disabled" in data["error"].lower()
    assert called is False


def test_emeet_source_selection_is_fixed(monkeypatch):
    monkeypatch.setattr(
        local_media,
        "_pactl_sources",
        lambda: (
            [
                {"name": "alsa_input.pci-built-in"},
                {"name": "alsa_input.usb-Sonix_EMEET_SmartCam_C950_serial.analog-stereo"},
            ],
            None,
        ),
    )

    source, error = local_media._emeet_audio_source()

    assert error is None
    assert source == "alsa_input.usb-Sonix_EMEET_SmartCam_C950_serial.analog-stereo"


def test_listen_once_captures_then_transcribes(monkeypatch, tmp_path):
    wav = tmp_path / "latest-emeet.wav"
    wav.write_bytes(b"RIFF-test")
    monkeypatch.setattr(
        local_media,
        "capture_emeet_audio",
        lambda: {"ok": True, "kind": "audio-capture", "path": str(wav), "seconds": 4},
    )
    monkeypatch.setattr(
        local_media,
        "transcribe_audio",
        lambda path: {
            "ok": True,
            "kind": "speech-to-text",
            "transcript": "AION local voice online.",
            "model": "/models/base.en.bin",
        },
    )

    data = local_media.listen_once()

    assert data["ok"] is True
    assert data["kind"] == "voice-listen"
    assert data["transcript"] == "AION local voice online."
    assert data["continuous_listening"] is False
    assert data["network_required"] is False


def test_transcribe_uses_fixed_whisper_cli_shape(monkeypatch, tmp_path):
    wav = tmp_path / "sample.wav"
    wav.write_bytes(b"RIFF-test")
    model = tmp_path / "model.bin"
    model.write_bytes(b"model")
    whisper = tmp_path / "whisper-cli"
    whisper.write_text("binary", encoding="utf-8")
    media_root = tmp_path / "media"
    media_root.mkdir()

    monkeypatch.setenv("AION_WHISPER_MODEL", str(model))
    monkeypatch.setenv("AION_WHISPER_BIN", str(whisper))
    monkeypatch.setattr(local_media, "_media_root", lambda: media_root)

    seen: tuple[str, ...] | None = None

    def fake_run(argv, **_kwargs):
        nonlocal seen
        seen = tuple(argv)
        (media_root / "latest-emeet-transcript.txt").write_text(
            "AION heard me.\n", encoding="utf-8"
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(local_media.subprocess, "run", fake_run)

    data = local_media.transcribe_audio(wav)

    assert data["ok"] is True
    assert data["transcript"] == "AION heard me."
    assert seen is not None
    assert seen[0] == str(whisper)
    assert seen[1:3] == ("-m", str(model))
    assert "-f" in seen
    assert str(wav) in seen
    assert "-otxt" in seen
    assert "-of" in seen
    assert "-np" in seen
    assert "-nt" in seen


def test_inventory_rejects_unknown_kind():
    try:
        local_media.inventory("screen")
    except ValueError as exc:
        assert "camera" in str(exc)
        assert "audio" in str(exc)
        assert "runtime" in str(exc)
    else:
        raise AssertionError("unknown media kind should fail closed")
