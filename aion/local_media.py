"""Read-only local media discovery for AION OS.

This module intentionally performs inventory only. It does not capture audio,
open cameras, record files, or accept caller-supplied device paths.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


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
        "capture_enabled": False,
        "error": error,
    }


def runtime_inventory() -> dict[str, Any]:
    """Report installed local media/STT/TTS building blocks without executing them."""
    tools = {name: shutil.which(name) for name in MEDIA_TOOLS}
    modules = {
        name: importlib.util.find_spec(name) is not None
        for name in PYTHON_MEDIA_MODULES
    }
    return {
        "ok": True,
        "kind": "media-runtime",
        "tools": tools,
        "python_modules": modules,
        "capture_enabled": False,
        "network_required": False,
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
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = inventory(kind)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
