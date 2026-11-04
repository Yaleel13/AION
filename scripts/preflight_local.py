#!/usr/bin/env python3
"""Passively assess whether this checkout is ready for local daily use."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv/bin/python"
REQUIRED_PYTHON_MODULES = ("fastapi", "httpx", "mcp", "dotenv")
REQUIRED_NODE_FILES = ("package.json", "node_modules")
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
CONFIG_LINE = re.compile(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)")
CONFIG_KEYS = frozenset({
    "AION_AUDIO_CAPTURE_ENABLED",
    "AION_OWNER_TOKEN",
    "AION_RUNTIME_MODE",
})
VOICE_FILES = (
    Path.home() / ".local/bin/whisper-cli",
    Path.home() / ".local/share/aion/whisper.cpp/models/ggml-tiny.en.bin",
    Path.home() / ".local/share/aion/piper/en_US-ryan-medium.onnx",
    Path.home() / ".local/share/aion/piper/en_US-ryan-medium.onnx.json",
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _check(
    name: str,
    status: str,
    detail: str,
    next_step: str,
    scope: str = "startup",
) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "next_step": next_step,
        "scope": scope,
    }


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _config(path: Path) -> tuple[dict[str, str], str]:
    if not path.is_file():
        return {}, "missing"
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}, "unreadable"

    values: dict[str, str] = {}
    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = CONFIG_LINE.fullmatch(stripped)
        if not match:
            return {}, "malformed"
        key, value = match.groups()
        if key not in CONFIG_KEYS:
            continue
        value = value.strip()
        if value[:1] in {"'", '"'}:
            if len(value) < 2 or value[-1] != value[0]:
                return {}, "malformed"
            value = value[1:-1]
        values[key] = value
    return values, "ok"


def _configured(values: dict[str, str], name: str) -> bool:
    return bool(values.get(name, "").strip())


def _loopback_json(url: str, timeout: float) -> dict[str, Any] | None:
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        return None
    try:
        with build_opener(_NoRedirect).open(url, timeout=timeout) as response:
            payload = json.load(response)
    except (HTTPError, OSError, URLError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _ollama_models() -> set[str] | None:
    payload = _loopback_json(OLLAMA_TAGS_URL, timeout=2)
    if payload is None:
        return None
    models = payload.get("models") if isinstance(payload, dict) else None
    return {
        str(item.get("name"))
        for item in models
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    } if isinstance(models, list) else set()


def _port_occupant(port: int) -> str:
    if _port_available(port):
        return "available"
    if port == 8000:
        health = _loopback_json("http://127.0.0.1:8000/health", timeout=1)
        if health and health.get("status") == "ok" and health.get("runtime") == "agent-v1":
            return "aion"
    return "unknown"


def _emeet_source() -> bool | None:
    pactl = shutil.which("pactl")
    if not pactl:
        return None
    try:
        completed = subprocess.run(
            (pactl, "list", "short", "sources"),
            capture_output=True, text=True, timeout=3, check=False,
        )
    except OSError:
        return None
    return completed.returncode == 0 and "emeet_smartcam_c950" in completed.stdout.lower()


def collect(root: Path = ROOT) -> dict[str, Any]:
    env, env_status = _config(root / ".env")
    local_env, local_env_status = _config(root / ".env.local")
    checks: list[dict[str, str]] = []
    checks.append(_check(
        "python-venv", "ok" if VENV_PYTHON.is_file() else "missing",
        ".venv/bin/python is present." if VENV_PYTHON.is_file() else ".venv/bin/python is missing.",
        "Create the virtual environment and install requirements with the documented setup." if not VENV_PYTHON.is_file() else "Use .venv/bin/python for runtime and checks.",
    ))
    missing_modules = list(REQUIRED_PYTHON_MODULES)
    if VENV_PYTHON.is_file():
        try:
            completed = subprocess.run(
                (str(VENV_PYTHON), "-c", "import fastapi, httpx, mcp, dotenv"),
                capture_output=True, text=True, timeout=10, check=False,
            )
            if completed.returncode == 0:
                missing_modules = []
        except OSError:
            pass
    checks.append(_check(
        "python-dependencies", "ok" if not missing_modules else "missing",
        "Required Python modules are importable." if not missing_modules else "One or more required Python modules are unavailable.",
        "Run .venv/bin/pip install -r requirements.txt after reviewing dependency changes." if missing_modules else "No action required.",
    ))
    missing_node = [name for name in REQUIRED_NODE_FILES if not (root / name).exists()]
    checks.append(_check(
        "node-dependencies", "ok" if shutil.which("node") and not missing_node else "missing",
        "Node and local frontend dependencies are available." if not missing_node and shutil.which("node") else "Node or node_modules is unavailable.",
        "Run npm ci after reviewing the lockfile." if missing_node or not shutil.which("node") else "No action required.",
    ))
    for label, port in (("runtime-port", 8000), ("boardroom-port", 3000)):
        occupant = _port_occupant(port)
        checks.append(_check(
            label, "ok" if occupant == "available" else f"occupied-{occupant}",
            f"Loopback port {port} is available." if occupant == "available" else (
                f"Loopback port {port} is occupied by a verified AION runtime."
                if occupant == "aion"
                else f"Loopback port {port} is occupied by an unknown listener."
            ),
            "No action required." if occupant == "available" else "Use another port or stop only a service you own.",
        ))
    local_mode = env.get("AION_RUNTIME_MODE", "").strip().lower() == "local"
    configuration_available = env_status == "ok" and local_env_status == "ok"
    checks.append(_check(
        "runtime-configuration",
        "ok" if configuration_available and local_mode and _configured(env, "AION_OWNER_TOKEN") and _configured(local_env, "AION_OWNER_TOKEN") else "incomplete",
        "Local mode and owner-token presence are configured." if configuration_available and local_mode and _configured(env, "AION_OWNER_TOKEN") and _configured(local_env, "AION_OWNER_TOKEN") else (
            "One or both local configuration files are unavailable or malformed."
            if not configuration_available
            else "Local mode or owner-token presence is not configured in both local environment files."
        ),
        "Set matching owner tokens privately in .env and .env.local and enable AION_RUNTIME_MODE=local when ready.",
    ))
    models = _ollama_models()
    if models is None:
        checks.append(_check("ollama", "unavailable", "Ollama did not answer on loopback.", "Start Ollama and verify http://127.0.0.1:11434/api/tags."))
    elif "aion:latest" not in models:
        checks.append(_check("ollama", "missing", "Ollama is reachable but aion:latest is not installed.", "Create or pull the approved local AION model."))
    else:
        checks.append(_check("ollama", "ok", "Loopback Ollama and aion:latest are available.", "No action required."))
    missing_voice = [str(path) for path in VOICE_FILES if not path.is_file()]
    piper = shutil.which("piper")
    capture_enabled = local_mode and env.get("AION_AUDIO_CAPTURE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    emeet = _emeet_source()
    checks.append(_check(
        "emeet-input", "ok" if emeet is True else "unavailable",
        "EMEET input is listed without opening the microphone." if emeet is True else "EMEET input was not found or PulseAudio/PipeWire listing is unavailable.",
        "Connect the EMEET device and confirm pactl lists its source." if emeet is not True else "No action required.",
        "voice",
    ))
    checks.append(_check(
        "voice-prerequisites", "ok" if not missing_voice and piper and capture_enabled else "incomplete",
        "Voice prerequisites are present, but the voice flow is not implemented." if not missing_voice and piper and capture_enabled else "Voice remains unavailable; Piper, voice artifacts, or the explicit capture gate is unavailable.",
        "Install/configure Piper, verify model files, and enable capture only before an explicit owner-initiated test.",
        "voice",
    ))
    local_ready = all(item["status"] == "ok" for item in checks if item["scope"] == "startup")
    voice_ready = False
    return {
        "ok": local_ready,
        "local_ready": local_ready,
        "voice_ready": voice_ready,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = collect()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Local startup readiness: {'READY' if report['local_ready'] else 'NOT READY'}; "
            "voice: UNAVAILABLE (the authorized voice flow is not implemented)."
        )
        for item in report["checks"]:
            print(f"{item['status'].upper():11} {item['name']}: {item['detail']} Next: {item['next_step']}")
    return 0 if report["local_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
