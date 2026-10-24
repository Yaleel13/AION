"""Local media discovery and explicitly gated capture for AION OS.

Discovery is read-only. Capture remains fail-closed unless the owner enables a
specific local gate. No caller-supplied device paths, durations, commands, or
output paths are accepted.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from aion.durable.paths import resolve_durable_paths


MEDIA_TOOLS = (
    "ffmpeg",
    "ffplay",
    "pactl",
    "parec",
    "pw-record",
    "arecord",
    "whisper-cli",
    "whisper",
    "piper",
    "espeak-ng",
)

PYTHON_MEDIA_MODULES = (
    "faster_whisper",
    "whisper",
    "vosk",
    "sounddevice",
)

EMEET_AUDIO_MARKER = "emeet_smartcam_c950"
AUDIO_CAPTURE_SECONDS = 4
DEFAULT_WHISPER_MODEL = (
    Path.home() / ".local/share/aion/whisper.cpp/models/ggml-base.en.bin"
)
DEFAULT_WHISPER_BIN = Path.home() / ".local/bin/whisper-cli"


def _env_enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def audio_capture_enabled() -> bool:
    return (
        (os.getenv("AION_RUNTIME_MODE") or "").strip().lower() == "local"
        and _env_enabled("AION_AUDIO_CAPTURE_ENABLED")
    )


def _media_root() -> Path:
    root = resolve_durable_paths().root / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


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


def camera_inventory() -> dict[str, Any]:
    devices: list[dict[str, Any]] = []
    for sysfs in sorted(Path("/sys/class/video4linux").glob("video*")):
        name_file = sysfs / "name"
        try:
            name = name_file.read_text(encoding="utf-8").strip()
        except OSError:
            name = sysfs.name
        device = Path("/dev") / sysfs.name
        devices.append(
            {
                "device": str(device),
                "name": name,
                "exists": device.exists(),
                "readable": device.exists() and device.stat().st_mode is not None,
            }
        )

    return {
        "ok": True,
        "kind": "camera",
        "count": len(devices),
        "devices": devices,
        "capture_enabled": False,
    }


def _pactl_sources() -> tuple[list[dict[str, Any]], str | None]:
    if not shutil.which("pactl"):
        return [], "pactl is unavailable"
    try:
        completed = subprocess.run(
            ("pactl", "list", "short", "sources"),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
    except OSError as exc:
        return [], str(exc)
    if completed.returncode != 0:
        return [], completed.stderr.strip() or f"pactl exited {completed.returncode}"

    sources: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        sources.append(
            {
                "id": fields[0],
                "name": fields[1],
                "driver": fields[2] if len(fields) > 2 else None,
                "sample_spec": fields[3] if len(fields) > 3 else None,
                "state": fields[4] if len(fields) > 4 else None,
            }
        )
    return sources, None


def _emeet_audio_source() -> tuple[str | None, str | None]:
    sources, error = _pactl_sources()
    if error:
        return None, error
    for source in sources:
        name = str(source.get("name") or "")
        if EMEET_AUDIO_MARKER in name.lower() and not name.endswith(".monitor"):
            return name, None
    return None, "EMEET SmartCam C950 microphone source was not found"


def audio_inventory() -> dict[str, Any]:
    sources, error = _pactl_sources()
    default_source: str | None = None
    if shutil.which("pactl"):
        try:
            completed = subprocess.run(
                ("pactl", "get-default-source"),
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
                shell=False,
            )
            if completed.returncode == 0:
                default_source = completed.stdout.strip() or None
        except OSError:
            pass

    return {
        "ok": error is None,
        "kind": "audio-input",
        "count": len(sources),
        "default_source": default_source,
        "sources": sources,
        "capture_enabled": audio_capture_enabled(),
        "error": error,
    }


def runtime_inventory() -> dict[str, Any]:
    """Report installed local media/STT/TTS building blocks without executing them."""
    tools = {name: shutil.which(name) for name in MEDIA_TOOLS}
    if tools["whisper-cli"] is None:
        tools["whisper-cli"] = _whisper_binary()
    modules = {
        name: importlib.util.find_spec(name) is not None
        for name in PYTHON_MEDIA_MODULES
    }
    whisper_model = _whisper_model()
    return {
        "ok": True,
        "kind": "media-runtime",
        "tools": tools,
        "python_modules": modules,
        "capture_enabled": audio_capture_enabled(),
        "audio_capture_enabled": audio_capture_enabled(),
        "whisper_model": str(whisper_model),
        "whisper_model_present": whisper_model.is_file(),
        "network_required": False,
    }


def capture_emeet_audio() -> dict[str, Any]:
    """Capture one fixed four-second EMEET sample when the owner gate is enabled."""
    if not audio_capture_enabled():
        return {
            "ok": False,
            "kind": "audio-capture",
            "capture_enabled": False,
            "error": "Audio capture is disabled. Set AION_AUDIO_CAPTURE_ENABLED=true in local mode.",
        }

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"ok": False, "kind": "audio-capture", "error": "ffmpeg is unavailable"}

    source, error = _emeet_audio_source()
    if error or not source:
        return {"ok": False, "kind": "audio-capture", "error": error or "EMEET microphone unavailable"}

    output = _media_root() / "latest-emeet.wav"
    try:
        completed = subprocess.run(
            (
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "pulse",
                "-i",
                source,
                "-t",
                str(AUDIO_CAPTURE_SECONDS),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output),
            ),
            capture_output=True,
            text=True,
            timeout=AUDIO_CAPTURE_SECONDS + 8,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "kind": "audio-capture", "error": str(exc)}

    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        return {
            "ok": False,
            "kind": "audio-capture",
            "error": completed.stderr.strip() or "EMEET audio capture failed",
        }

    return {
        "ok": True,
        "kind": "audio-capture",
        "capture_enabled": True,
        "source": source,
        "seconds": AUDIO_CAPTURE_SECONDS,
        "sample_rate": 16000,
        "channels": 1,
        "path": str(output),
        "bytes": output.stat().st_size,
        "network_required": False,
    }


def transcribe_audio(path: Path) -> dict[str, Any]:
    whisper = _whisper_binary()
    model = _whisper_model()
    if not whisper:
        return {"ok": False, "kind": "speech-to-text", "error": "whisper-cli is unavailable"}
    if not model.is_file():
        return {"ok": False, "kind": "speech-to-text", "error": f"Whisper model is missing: {model}"}
    if not path.is_file():
        return {"ok": False, "kind": "speech-to-text", "error": "Captured audio file is missing"}

    output_prefix = _media_root() / "latest-emeet-transcript"
    output_txt = Path(f"{output_prefix}.txt")
    try:
        output_txt.unlink(missing_ok=True)
        completed = subprocess.run(
            (
                whisper,
                "-m",
                str(model),
                "-f",
                str(path),
                "-l",
                "en",
                "-t",
                "2",
                "-nt",
                "-np",
                "-otxt",
                "-of",
                str(output_prefix),
            ),
            capture_output=True,
            text=True,
            timeout=120,
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
        return {"ok": False, "kind": "speech-to-text", "error": "Whisper did not produce a transcript file"}

    transcript = output_txt.read_text(encoding="utf-8").strip()
    return {
        "ok": True,
        "kind": "speech-to-text",
        "transcript": transcript,
        "model": str(model),
        "network_required": False,
    }


def listen_once() -> dict[str, Any]:
    """One explicit push-to-talk style turn: capture then locally transcribe."""
    captured = capture_emeet_audio()
    if not captured.get("ok"):
        return captured
    transcribed = transcribe_audio(Path(str(captured["path"])))
    if not transcribed.get("ok"):
        return {
            **transcribed,
            "capture": captured,
        }
    return {
        "ok": True,
        "kind": "voice-listen",
        "transcript": transcribed["transcript"],
        "capture": captured,
        "stt_model": transcribed["model"],
        "network_required": False,
        "continuous_listening": False,
    }


def inventory(kind: str) -> dict[str, Any]:
    if kind == "camera":
        return camera_inventory()
    if kind == "audio":
        return audio_inventory()
    if kind == "runtime":
        return runtime_inventory()
    raise ValueError("kind must be 'camera', 'audio', or 'runtime'")


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "listen":
        payload = listen_once()
    else:
        try:
            payload = inventory(command)
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))
            return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
