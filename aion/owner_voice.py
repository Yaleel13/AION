"""Dedicated, owner-authorized local voice turn with temporary media only."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from aion import local_media
from aion.local_intelligence import local_model_name, ollama_base_url
from aion.local_voice import _whisper_binary, _whisper_model
from aion.local_voice_turn import _piper_voice

CAPTURE_SECONDS = 6
CAPTURE_TIMEOUT_SECONDS = 20
TRANSCRIBE_TIMEOUT_SECONDS = 90
SYNTHESIS_TIMEOUT_SECONDS = 90
PLAYBACK_TIMEOUT_SECONDS = 120
MODEL_TIMEOUT_SECONDS = 45
MAX_TEXT_CHARS = 2_000
MAX_MODEL_RESPONSE_BYTES = 64 * 1024
MINIMAL_ENVIRONMENT = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


def _configured() -> tuple[dict[str, str] | None, str | None]:
    if os.name != "posix" or not local_media.audio_capture_enabled():
        return None, "Voice is unavailable."
    ffmpeg, whisper, piper, ffplay = (
        shutil.which("ffmpeg"),
        _whisper_binary(),
        shutil.which("piper"),
        shutil.which("ffplay"),
    )
    model, voice = _whisper_model(), _piper_voice()
    voice_config = Path(f"{voice}.json")
    source, source_error = local_media._emeet_audio_source()
    if not all((ffmpeg, whisper, piper, ffplay, source)) or not model.is_file() or not voice.is_file() or not voice_config.is_file():
        return None, "Voice is unavailable."
    if source_error:
        return None, "Voice is unavailable."
    return {
        "ffmpeg": ffmpeg,
        "whisper": whisper,
        "piper": piper,
        "ffplay": ffplay,
        "source": source,
        "model": str(model),
        "voice": str(voice),
    }, None


def _ollama_url() -> str | None:
    try:
        parsed = urlparse(ollama_base_url())
    except ValueError:
        return None
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return None
    if parsed.username or parsed.password or parsed.params or parsed.query or parsed.fragment:
        return None
    return parsed.geturl().rstrip("/")


async def _run(argv: tuple[str, ...], timeout: int) -> bool:
    process: asyncio.subprocess.Process | None = None

    async def drain(stream: asyncio.StreamReader | None) -> None:
        if stream is None:
            return
        while await stream.read(4096):
            pass

    async def cleanup(readers: list[asyncio.Task[None]]) -> None:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
        await asyncio.gather(*readers, return_exceptions=True)

    async def settle(task: asyncio.Task[Any]) -> tuple[Any, bool]:
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        return task.result(), cancelled

    async def execute() -> bool:
        nonlocal process
        spawn = asyncio.create_task(asyncio.create_subprocess_exec(
            *argv,
            env=MINIMAL_ENVIRONMENT.copy(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        ))
        try:
            process = await asyncio.shield(spawn)
        except asyncio.CancelledError:
            process, _ = await settle(spawn)
            readers = [asyncio.create_task(drain(process.stdout)), asyncio.create_task(drain(process.stderr))]
            await settle(asyncio.create_task(cleanup(readers)))
            raise

        readers = [asyncio.create_task(drain(process.stdout)), asyncio.create_task(drain(process.stderr))]
        try:
            await process.wait()
            return process.returncode == 0
        finally:
            _, cancelled = await settle(asyncio.create_task(cleanup(readers)))
            if cancelled:
                raise asyncio.CancelledError

    try:
        async with asyncio.timeout(timeout):
            return await execute()
    except (OSError, TimeoutError):
        return False


async def _bounded_json(response: httpx.Response) -> dict[str, Any] | None:
    content_length = response.headers.get("content-length")
    if content_length and (not content_length.isdigit() or int(content_length) > MAX_MODEL_RESPONSE_BYTES):
        return None
    content = bytearray()
    async for chunk in response.aiter_bytes():
        if len(content) + len(chunk) > MAX_MODEL_RESPONSE_BYTES:
            return None
        content.extend(chunk)
    try:
        payload = json.loads(content)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


async def _model_ready(client: httpx.AsyncClient, base_url: str, model: str) -> bool:
    try:
        async with client.stream("GET", f"{base_url}/api/tags") as response:
            payload = await _bounded_json(response)
    except httpx.HTTPError:
        return False
    models = payload.get("models") if isinstance(payload, dict) else None
    return response.is_success and isinstance(models, list) and any(
        isinstance(item, dict) and item.get("name") == model for item in models
    )


async def _reply(client: httpx.AsyncClient, base_url: str, transcript: str) -> str | None:
    try:
        async with client.stream(
            "POST",
            f"{base_url}/api/chat",
            json={
                "model": local_model_name(),
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are AION. Reply briefly and truthfully."},
                    {"role": "user", "content": transcript},
                ],
                "options": {"num_predict": 96, "temperature": 0.3},
            },
        ) as response:
            payload = await _bounded_json(response)
    except httpx.HTTPError:
        return None
    message = payload.get("message") if isinstance(payload, dict) else None
    reply = message.get("content") if isinstance(message, dict) else None
    return reply.strip()[:MAX_TEXT_CHARS] if response.is_success and isinstance(reply, str) and reply.strip() else None


async def run_owner_voice_turn() -> dict[str, Any]:
    """Run one fixed capture, transcription, local reasoning, synthesis, and playback turn."""
    tools, error = _configured()
    base_url = _ollama_url()
    if tools is None or base_url is None:
        return {"ok": False, "status": "unavailable", "error": "Voice is unavailable."}

    timeout = httpx.Timeout(MODEL_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        if not await _model_ready(client, base_url, local_model_name()):
            return {"ok": False, "status": "unavailable", "error": "Voice is unavailable."}
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="aion-owner-voice-") as directory:
            temporary = Path(directory)
            captured = temporary / "capture.wav"
            transcript_file = temporary / "transcript.txt"
            reply_audio = temporary / "reply.wav"
            if not await _run((
                tools["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", "-f", "pulse",
                "-i", tools["source"], "-t", str(CAPTURE_SECONDS), "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(captured),
            ), CAPTURE_TIMEOUT_SECONDS) or not captured.is_file() or not captured.stat().st_size:
                return {"ok": False, "status": "failed", "error": "Voice turn failed."}
            prefix = temporary / "transcript"
            if not await _run((
                tools["whisper"], "-m", tools["model"], "-f", str(captured), "-l", "en", "-t", "2",
                "-nt", "-np", "-otxt", "-of", str(prefix),
            ), TRANSCRIBE_TIMEOUT_SECONDS):
                return {"ok": False, "status": "failed", "error": "Voice turn failed."}
            transcript_file = Path(f"{prefix}.txt")
            try:
                transcript = transcript_file.read_text(encoding="utf-8").strip()[:MAX_TEXT_CHARS]
            except (OSError, UnicodeError):
                transcript = ""
            if not transcript:
                return {"ok": False, "status": "failed", "error": "Voice turn failed."}
            reply = await _reply(client, base_url, transcript)
            if reply is None:
                return {"ok": False, "status": "failed", "error": "Voice turn failed."}
            if not await _run((
                tools["piper"], "-m", tools["voice"], "-f", str(reply_audio), "--", reply,
            ), SYNTHESIS_TIMEOUT_SECONDS) or not reply_audio.is_file() or not reply_audio.stat().st_size:
                return {"ok": False, "status": "failed", "error": "Voice turn failed."}
            if not await _run((tools["ffplay"], "-nodisp", "-autoexit", "-loglevel", "error", str(reply_audio)), PLAYBACK_TIMEOUT_SECONDS):
                return {"ok": False, "status": "failed", "error": "Voice turn failed."}
    return {
        "ok": True, "status": "succeeded", "transcript": transcript, "reply": reply,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "continuous_listening": False, "durable_memory_written": False,
    }
