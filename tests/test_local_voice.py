from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from aion import local_voice


def test_voice_defaults_to_tiny_model_and_four_threads(monkeypatch):
    monkeypatch.delenv("AION_WHISPER_MODEL", raising=False)
    monkeypatch.setattr(local_voice.os, "cpu_count", lambda: 4)

    assert local_voice._whisper_model().name == "ggml-tiny.en.bin"
    assert local_voice._threads() == 4


def test_voice_threads_never_exceed_available_cpu(monkeypatch):
    monkeypatch.setattr(local_voice.os, "cpu_count", lambda: 2)
    assert local_voice._threads() == 2


def test_voice_capture_defaults_to_six_seconds_and_is_bounded(monkeypatch):
    monkeypatch.delenv("AION_AUDIO_CAPTURE_SECONDS", raising=False)
    assert local_voice._voice_capture_seconds() == 6

    monkeypatch.setenv("AION_AUDIO_CAPTURE_SECONDS", "2")
    assert local_voice._voice_capture_seconds() == 3

    monkeypatch.setenv("AION_AUDIO_CAPTURE_SECONDS", "30")
    assert local_voice._voice_capture_seconds() == 10

    monkeypatch.setenv("AION_AUDIO_CAPTURE_SECONDS", "invalid")
    assert local_voice._voice_capture_seconds() == 6


def test_voice_capture_temporarily_overrides_media_duration(monkeypatch):
    monkeypatch.setenv("AION_AUDIO_CAPTURE_SECONDS", "7")
    original = local_voice.local_media.AUDIO_CAPTURE_SECONDS
    seen = None

    def fake_capture():
        nonlocal seen
        seen = local_voice.local_media.AUDIO_CAPTURE_SECONDS
        return {"ok": True, "seconds": seen, "path": "/tmp/test.wav"}

    monkeypatch.setattr(local_voice.local_media, "capture_emeet_audio", fake_capture)

    result = local_voice.capture_emeet_audio()

    assert result["ok"] is True
    assert seen == 7
    assert local_voice.local_media.AUDIO_CAPTURE_SECONDS == original


def test_transcribe_uses_laptop_tuned_whisper_shape(monkeypatch, tmp_path):
    wav = tmp_path / "sample.wav"
    wav.write_bytes(b"RIFF-test")
    model = tmp_path / "ggml-tiny.en.bin"
    model.write_bytes(b"model")
    whisper = tmp_path / "whisper-cli"
    whisper.write_text("binary", encoding="utf-8")
    media_root = tmp_path / "media"
    media_root.mkdir()

    monkeypatch.setenv("AION_WHISPER_MODEL", str(model))
    monkeypatch.setenv("AION_WHISPER_BIN", str(whisper))
    monkeypatch.setenv("AION_WHISPER_PROMPT", "AION. Yaleel, pronounced YahLee-el.")
    monkeypatch.setattr(local_voice, "_media_root", lambda: media_root)
    monkeypatch.setattr(local_voice.os, "cpu_count", lambda: 4)

    seen: tuple[str, ...] | None = None

    def fake_run(argv, **_kwargs):
        nonlocal seen
        seen = tuple(argv)
        (media_root / "latest-emeet-transcript.txt").write_text(
            "Hello, AION. This is YahLee-el.\n", encoding="utf-8"
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(local_voice.subprocess, "run", fake_run)

    data = local_voice.transcribe(wav)

    assert data["ok"] is True
    assert data["transcript"] == "Hello, AION. This is YahLee-el."
    assert data["threads"] == 4
    assert data["best_of"] == 1
    assert data["beam_size"] == 1
    assert data["temperature_fallback"] is False
    assert seen is not None
    assert seen[0] == str(whisper)
    assert ("-m", str(model)) == seen[1:3]
    assert "-bo" in seen and seen[seen.index("-bo") + 1] == "1"
    assert "-bs" in seen and seen[seen.index("-bs") + 1] == "1"
    assert "-nf" in seen
    assert "--prompt" in seen
    assert seen[seen.index("--prompt") + 1] == "AION. Yaleel, pronounced YahLee-el."
    assert "-t" in seen and seen[seen.index("-t") + 1] == "4"
    assert "-otxt" in seen
    assert "-np" in seen
    assert "-nt" in seen


def test_listen_once_reuses_gated_capture(monkeypatch, tmp_path):
    wav = tmp_path / "latest-emeet.wav"
    wav.write_bytes(b"RIFF-test")
    monkeypatch.setattr(
        local_voice,
        "capture_emeet_audio",
        lambda: {"ok": True, "kind": "audio-capture", "path": str(wav), "seconds": 6},
    )
    monkeypatch.setattr(
        local_voice,
        "transcribe",
        lambda path: {
            "ok": True,
            "kind": "speech-to-text",
            "transcript": "AION local voice online.",
            "model": "/models/tiny.en.bin",
            "threads": 4,
        },
    )

    data = local_voice.listen_once()

    assert data["ok"] is True
    assert data["kind"] == "voice-listen"
    assert data["transcript"] == "AION local voice online."
    assert data["capture"]["seconds"] == 6
    assert data["stt_threads"] == 4
    assert data["continuous_listening"] is False
    assert data["network_required"] is False
