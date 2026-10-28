"""Optimized one-shot local voice transcription for AION OS.

This module reuses the explicitly gated EMEET capture path from ``local_media``
and applies a laptop-tuned whisper.cpp configuration. It accepts no caller
arguments or device paths and performs no network access.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from aion import local_media
from aion.durable.paths import resolve_durable_paths


DEFAULT_WHISPER_BIN = Path.home() / ".local/bin/whisper-cli"
DEFAULT_WHISPER_MODEL = (
    Path.home() / ".local/share/aion/whisper.cpp/models/ggml-tiny.en.bin"
)
DEFAULT_PROMPT = (
    "AION. Yaleel, pronounced YahLee-el. YaliTek. Elaria. "
    "Local voice recognition and personal assistant conversation."
)
MAX_THREADS = 4
DEFAULT_VOICE_CAPTURE_SECONDS = 6
MIN_VOICE_CAPTURE_SECONDS = 3
MAX_VOICE_CAPTURE_SECONDS = 10


def _whisper_binary() -> str | None:
    configured = (os.getenv("AION_WHISPER_BIN") or "").strip()
    if configured:
        path = Path(configured).expanduser()
        return str(path) if path.is_file() else None
    detected = shutil.which("whisper-cli")
    if detected:
        return detected
    return str(DEFAULT_WHISPER_BIN) if DEFAULT_WHISPER_BIN.is_file() else None


def _whisper_model() -> Path:
    configured = (os.getenv("AION_WHISPER_MODEL") or "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_WHISPER_MODEL


def _threads() -> int:
    available = os.cpu_count() or 1
    return max(1, min(MAX_THREADS, available))


def _prompt() -> str:
    return (os.getenv("AION_WHISPER_PROMPT") or DEFAULT_PROMPT).strip()


def _voice_capture_seconds() -> int:
    raw = (os.getenv("AION_AUDIO_CAPTURE_SECONDS") or str(DEFAULT_VOICE_CAPTURE_SECONDS)).strip()
    try:
        seconds = int(raw)
    except ValueError:
        return DEFAULT_VOICE_CAPTURE_SECONDS
    return max(MIN_VOICE_CAPTURE_SECONDS, min(MAX_VOICE_CAPTURE_SECONDS, seconds))


def capture_emeet_audio() -> dict[str, Any]:
    """Run the gated EMEET capture with a bounded voice-specific duration."""
    original_seconds = local_media.AUDIO_CAPTURE_SECONDS
    local_media.AUDIO_CAPTURE_SECONDS = _voice_capture_seconds()
    try:
        return local_media.capture_emeet_audio()
    finally:
        local_media.AUDIO_CAPTURE_SECONDS = original_seconds


def _media_root() -> Path:
    root = resolve_durable_paths().root / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


def transcribe(path: Path) -> dict[str, Any]:
    whisper = _whisper_binary()
    model = _whisper_model()
    if not whisper:
        return {"ok": False, "kind": "speech-to-text", "error": "whisper-cli is unavailable"}
    if not model.is_file():
        return {
            "ok": False,
            "kind": "speech-to-text",
            "error": f"Whisper model is missing: {model}",
        }
    if not path.is_file():
        return {"ok": False, "kind": "speech-to-text", "error": "Captured audio file is missing"}

    output_prefix = _media_root() / "latest-emeet-transcript"
    output_txt = Path(f"{output_prefix}.txt")
    output_txt.unlink(missing_ok=True)

    argv = (
        whisper,
        "-m",
        str(model),
        "-f",
        str(path),
        "-l",
        "en",
        "-t",
        str(_threads()),
        "-bo",
        "1",
        "-bs",
        "1",
        "-nf",
        "--prompt",
        _prompt(),
        "-nt",
        "-np",
        "-otxt",
        "-of",
        str(output_prefix),
    )

    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "kind": "speech-to-text", "error": str(exc)}

    if completed.returncode != 0:
        return {
            "ok": False,
            "kind": "speech-to-text",
            "error": completed.stderr.strip() or "Whisper transcription failed",
        }
    if not output_txt.is_file():
        return {
            "ok": False,
            "kind": "speech-to-text",
            "error": "Whisper did not produce a transcript file",
        }

    transcript = output_txt.read_text(encoding="utf-8").strip()
    return {
        "ok": True,
        "kind": "speech-to-text",
        "transcript": transcript,
        "model": str(model),
        "threads": _threads(),
        "best_of": 1,
        "beam_size": 1,
        "temperature_fallback": False,
        "prompted": True,
        "network_required": False,
    }


def listen_once() -> dict[str, Any]:
    started = time.perf_counter()
    captured = capture_emeet_audio()
    captured_at = time.perf_counter()
    if not captured.get("ok"):
        return captured

    transcribed = transcribe(Path(str(captured["path"])))
    transcribed_at = time.perf_counter()
    if not transcribed.get("ok"):
        return {**transcribed, "capture": captured}

    return {
        "ok": True,
        "kind": "voice-listen",
        "transcript": transcribed["transcript"],
        "capture": captured,
        "stt_model": transcribed["model"],
        "stt_threads": transcribed["threads"],
        "timings_ms": {
            "capture": round((captured_at - started) * 1000),
            "stt": round((transcribed_at - captured_at) * 1000),
            "listen_total": round((transcribed_at - started) * 1000),
        },
        "network_required": False,
        "continuous_listening": False,
    }


def main() -> int:
    payload = listen_once()
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
