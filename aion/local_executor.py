"""AION OS local controlled executor.

Provides fixed, typed local capabilities for the machine running AION.
This is intentionally NOT an arbitrary shell.

Core principles:
- no API keys required
- no shell=True
- no caller-supplied executable or argv
- fixed working-directory policy
- bounded execution time
- bounded output
- no sudo/root escalation
- read/test/build plus explicitly gated local media capture capabilities
"""

from __future__ import annotations

import asyncio
import os
import platform
import re
import signal
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_OUTPUT = 12_000
DEFAULT_TIMEOUT = 120
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAFE_PATH = "/usr/local/bin:/usr/bin:/bin"
MINIMAL_ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": SAFE_PATH,
}


@dataclass(frozen=True)
class Capability:
    name: str
    argv: tuple[str, ...]
    timeout: int = DEFAULT_TIMEOUT
    cwd: Path = PROJECT_ROOT
    classification: str = "read"


CAPABILITIES: dict[str, Capability] = {
    "system.info": Capability(
        name="system.info",
        argv=("uname", "-a"),
    ),
    "system.storage": Capability(
        name="system.storage",
        argv=("df", "-h", str(PROJECT_ROOT)),
    ),
    "system.memory": Capability(
        name="system.memory",
        argv=("free", "-h"),
    ),
    "system.processes": Capability(
        name="system.processes",
        argv=("ps", "-eo", "pid,ppid,comm,%cpu,%mem"),
    ),
    "media.audio.inputs": Capability(
        name="media.audio.inputs",
        argv=(sys.executable, "-m", "aion.local_media", "audio"),
    ),
    "media.camera.inputs": Capability(
        name="media.camera.inputs",
        argv=(sys.executable, "-m", "aion.local_media", "camera"),
    ),
    "media.runtime": Capability(
        name="media.runtime",
        argv=(sys.executable, "-m", "aion.local_media", "runtime"),
    ),
    "media.voice.listen": Capability(
        name="media.voice.listen",
        argv=(sys.executable, "-m", "aion.local_voice"),
        timeout=150,
        classification="capture",
    ),
    "media.voice.ask": Capability(
        name="media.voice.ask",
        argv=(sys.executable, "-m", "aion.local_voice_turn"),
        timeout=300,
        classification="capture",
    ),
    "git.status": Capability(
        name="git.status",
        argv=("git", "status", "--short", "--branch"),
    ),
    "git.diff": Capability(
        name="git.diff",
        argv=("git", "diff", "--stat"),
    ),
    "project.inspect": Capability(
        name="project.inspect",
        argv=("git", "rev-parse", "--short", "HEAD"),
    ),
    "project.test": Capability(
        name="project.test",
        argv=(sys.executable, "-m", "pytest", "tests/", "-q"),
        timeout=180,
        classification="test",
    ),
    "project.lint": Capability(
        name="project.lint",
        argv=("npm", "run", "lint"),
        timeout=180,
        classification="test",
    ),
    "project.build": Capability(
        name="project.build",
        argv=("npm", "run", "build"),
        timeout=240,
        classification="test",
    ),
}


def _resolved_argv(argv: tuple[str, ...]) -> tuple[str, ...] | None:
    if not argv:
        return None
    executable = argv[0] if os.path.isabs(argv[0]) else shutil.which(argv[0], path=SAFE_PATH)
    if not executable:
        return None
    return (executable, *argv[1:])


def local_executor_available() -> bool:
    """Return whether this process is running in an eligible local OS runtime."""
    mode = (os.getenv("AION_RUNTIME_MODE") or "").strip().lower()
    return mode == "local" and os.name == "posix" and PROJECT_ROOT.exists()


def executor_status() -> dict[str, Any]:
    return {
        "connected": local_executor_available(),
        "mode": "local-controlled" if local_executor_available() else None,
        "project_root": str(PROJECT_ROOT),
        "platform": platform.system().lower(),
        "arbitrary_commands_enabled": False,
        "sudo_enabled": False,
        "capabilities": sorted(CAPABILITIES),
    }


def _safe_summary(name: str, stdout: bytes) -> str | None:
    output = stdout.decode("utf-8", errors="ignore").strip()
    if name == "project.inspect":
        return output if re.fullmatch(r"[0-9a-f]{7,40}", output) else None
    if name == "git.status":
        return "clean" if not output else "changes detected"
    if name == "system.info":
        return f"{platform.system().lower()} inspection completed"
    return None


async def execute_capability(name: str) -> dict[str, Any]:
    """Execute one predefined capability.

    `name` selects from the static registry. No command text, arguments,
    paths, environment overrides, or shell fragments are accepted.
    """
    if not local_executor_available():
        return {
            "ok": False,
            "capability": name,
            "error": "Local executor is not enabled for this runtime.",
        }

    capability = CAPABILITIES.get(name)
    if capability is None:
        return {
            "ok": False,
            "capability": name,
            "error": "Unsupported local capability.",
            "allowed": sorted(CAPABILITIES),
        }

    argv = _resolved_argv(capability.argv)
    if argv is None:
        return {
            "ok": False,
            "capability": name,
            "error": f"Required executable is unavailable: {capability.argv[0]}",
        }

    output = bytearray()
    stdout = bytearray()
    truncated = False
    process: asyncio.subprocess.Process | None = None

    async def drain(stream: asyncio.StreamReader, destination: bytearray) -> None:
        nonlocal truncated
        while chunk := await stream.read(4096):
            remaining = MAX_OUTPUT - len(output)
            output.extend(chunk[:remaining])
            destination.extend(chunk[:remaining])
            truncated |= len(chunk) > remaining

    async def cleanup(
        child: asyncio.subprocess.Process, readers: list[asyncio.Task]
    ) -> None:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await child.wait()
        await asyncio.gather(*readers)

    async def settle(task: asyncio.Task) -> tuple[Any, bool]:
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        return task.result(), cancelled

    async def execute() -> None:
        nonlocal process

        async def start_process() -> asyncio.subprocess.Process:
            return await asyncio.create_subprocess_exec(
                *argv,
                cwd=capability.cwd,
                env=MINIMAL_ENVIRONMENT.copy(),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )

        spawn = asyncio.create_task(start_process())
        try:
            process = await asyncio.shield(spawn)
        except asyncio.CancelledError:
            process, _ = await settle(spawn)
            readers = [
                asyncio.create_task(drain(process.stdout, stdout)),
                asyncio.create_task(drain(process.stderr, bytearray())),
            ]
            await settle(asyncio.create_task(cleanup(process, readers)))
            raise

        readers = [
            asyncio.create_task(drain(process.stdout, stdout)),
            asyncio.create_task(drain(process.stderr, bytearray())),
        ]
        try:
            await process.wait()
        finally:
            _, cancelled = await settle(asyncio.create_task(cleanup(process, readers)))
            if cancelled:
                raise asyncio.CancelledError

    status = "failed"
    try:
        async with asyncio.timeout(capability.timeout):
            await execute()
        status = "succeeded" if process and process.returncode == 0 else "failed"
    except TimeoutError:
        status = "timeout"
    except OSError:
        return {
            "ok": False,
            "capability": name,
            "classification": capability.classification,
            "error": "Local capability is unavailable.",
        }

    return {
        "ok": status == "succeeded",
        "executor": "aion-local-controlled",
        "mode": "local-controlled",
        "capability": capability.name,
        "classification": capability.classification,
        "status": status,
        "exit_code": process.returncode if process else None,
        "summary": _safe_summary(capability.name, bytes(stdout)),
        "output_truncated": truncated,
        "cwd": str(capability.cwd),
        "arbitrary_commands_enabled": False,
        "sudo_enabled": False,
    }
