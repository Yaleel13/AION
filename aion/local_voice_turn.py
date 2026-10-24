"""One explicit local spoken conversation turn for AION OS.

Flow: EMEET capture -> whisper.cpp -> loopback Ollama -> Piper -> local playback.
The capability is one-shot only, accepts no caller-supplied commands/paths, and
never contacts a non-loopback reasoning endpoint.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from aion.durable.paths import resolve_durable_paths
from aion.local_intelligence import local_context_size, local_model_name, ollama_base_url
from aion.local_voice import listen_once


DEFAULT_PIPER_VOICE = Path.home() / ".local/share/aion/piper/en_US-ryan-medium.onnx"
VOICE_SYSTEM_PROMPT = (
    "You are AION. Reply naturally for spoken conversation. Be concise unless the "
    "user asks for depth. Do not mention implementation details unless asked."
)
OLLAMA_TIMEOUT_SECONDS = 120
TTS_TIMEOUT_SECONDS = 90
PLAYBACK_TIMEOUT_SECONDS = 90


def _local_mode() -> bool:
    return (os.getenv("AION_RUNTIME_MODE") or "").strip().lower() == "local"


def _loopback_ollama_url() -> str | None:
    value = ollama_base_url()
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return None
    return value.rstrip("/")


def _piper_voice() -> Path:
    configured = (os.getenv("AION_PIPER_VOICE") or "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_PIPER_VOICE


def _media_root() -> Path:
    root = resolve_durable_paths().root / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _playback_enabled() -> bool:
    raw = (os.getenv("AION_VOICE_PLAYBACK_ENABLED") or "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def reason_locally(text: str) -> dict[str, Any]:
    if not _local_mode():
        return {"ok": False, "kind": "voice-reasoning", "error": "Local runtime mode is required"}

    base_url = _loopback_ollama_url()
    if not base_url:
        return {
            "ok": False,
            "kind": "voice-reasoning",
            "error": "Voice reasoning requires a loopback Ollama endpoint",
        }

    payload = {
        "model": local_model_name(),
        "messages": [
            {"role": "system", "content": VOICE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_ctx": local_context_size(), "temperature": 0.4},
    }
    request = Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:  # noqa: S310 - loopback enforced above
            data = json.load(response)
    except Exception as exc:  # noqa: BLE001 - voice turn must return a bounded failure
        return {"ok": False, "kind": "voice-reasoning", "error": f"{type(exc).__name__}: {exc}"}

    message = data.get("message") if isinstance(data, dict) else None
    reply = message.get("content") if isinstance(message, dict) else None
    if not isinstance(reply, str) or not reply.strip():
        return {"ok": False, "kind": "voice-reasoning", "error": "Ollama returned no reply"}

    return {
        "ok": True,
        "kind": "voice-reasoning",
        "reply": reply.strip(),
        "model": local_model_name(),
        "network_required": False,
    }


def synthesize_reply(text: str) -> dict[str, Any]:
    piper = shutil.which("piper")
    if not piper:
        return {"ok": False, "kind": "text-to-speech", "error": "piper is unavailable"}

    voice = _piper_voice()
    config = Path(f"{voice}.json")
    if not voice.is_file() or not config.is_file():
        return {
            "ok": False,
            "kind": "text-to-speech",
            "error": f"Piper voice is missing: {voice}",
            "voice": str(voice),
        }

    output = _media_root() / "latest-aion-reply.wav"
    output.unlink(missing_ok=True)
    try:
        completed = subprocess.run(
            (piper, "-m", str(voice), "-f", str(output), "--", text),
            capture_output=True,
            text=True,
            timeout=TTS_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "kind": "text-to-speech", "error": str(exc)}

    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        return {
            "ok": False,
            "kind": "text-to-speech",
            "error": completed.stderr.strip() or "Piper synthesis failed",
        }

    return {
        "ok": True,
        "kind": "text-to-speech",
        "voice": str(voice),
        "path": str(output),
        "bytes": output.stat().st_size,
        "network_required": False,
    }


def play_reply(path: Path) -> dict[str, Any]:
    if not _playback_enabled():
        return {"ok": True, "kind": "voice-playback", "played": False, "disabled": True}

    ffplay = shutil.which("ffplay")
    if not ffplay:
        return {"ok": True, "kind": "voice-playback", "played": False, "error": "ffplay is unavailable"}

    try:
        completed = subprocess.run(
            (ffplay, "-nodisp", "-autoexit", "-loglevel", "error", str(path)),
            capture_output=True,
            text=True,
            timeout=PLAYBACK_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": True, "kind": "voice-playback", "played": False, "error": str(exc)}

    return {
        "ok": True,
        "kind": "voice-playback",
        "played": completed.returncode == 0,
        "error": completed.stderr.strip() or None if completed.returncode != 0 else None,
    }


def voice_turn() -> dict[str, Any]:
    heard = listen_once()
    if not heard.get("ok"):
        return heard

    transcript = str(heard.get("transcript") or "").strip()
    if not transcript:
        return {"ok": False, "kind": "voice-turn", "error": "No speech was transcribed", "listen": heard}

    reasoned = reason_locally(transcript)
    if not reasoned.get("ok"):
        return {**reasoned, "transcript": transcript}

    reply = str(reasoned["reply"])
    spoken = synthesize_reply(reply)
    if not spoken.get("ok"):
        return {
            **spoken,
            "kind": "voice-turn",
            "transcript": transcript,
            "reply": reply,
            "reasoning_model": reasoned.get("model"),
        }

    playback = play_reply(Path(str(spoken["path"])))
    return {
        "ok": True,
        "kind": "voice-turn",
        "transcript": transcript,
        "reply": reply,
        "reasoning_model": reasoned.get("model"),
        "tts_voice": spoken.get("voice"),
        "audio_path": spoken.get("path"),
        "played": playback.get("played", False),
        "playback_error": playback.get("error"),
        "network_required": False,
        "continuous_listening": False,
    }


def main() -> int:
    payload = voice_turn()
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
