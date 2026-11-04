"""One fixed Local Executive job; no caller-controlled execution parameters."""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
from typing import Any

from aion.local_executor import PROJECT_ROOT, local_executor_available

ARGV = (sys.executable, "-I", str(PROJECT_ROOT / "scripts/validate_runtime_syntax.py"))
JOB_ENV = {"LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
TIMEOUT_SECONDS = 30
MAX_OUTPUT_BYTES = 12_000


async def run_fixed_job(
    *,
    argv: tuple[str, ...],
    timeout_seconds: int,
    environment: dict[str, str],
    job: str,
    include_output: bool,
    include_duration: bool = False,
) -> dict[str, Any]:
    """Run one server-owned local job; cancellation kills its process group."""
    started_at = time.monotonic()
    if not local_executor_available() or os.name != "posix":
        result = {"ok": False, "job": job, "status": "unavailable"}
        if include_duration:
            result["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        return result

    output = bytearray()
    truncated = False
    process = None

    async def drain(stream: asyncio.StreamReader) -> None:
        nonlocal truncated
        while chunk := await stream.read(4096):
            remaining = MAX_OUTPUT_BYTES - len(output)
            output.extend(chunk[:remaining])
            truncated |= len(chunk) > remaining

    async def cleanup(process: asyncio.subprocess.Process, readers: list[asyncio.Task]) -> None:
        # Kill the session's group even if its leader exited: descendants can
        # otherwise keep running or hold inherited output pipes open.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()  # Reap our direct child.
        await asyncio.gather(*readers)

    async def settle(task: asyncio.Task) -> tuple[Any, bool]:
        """Finish ownership/cleanup work despite repeated cancellation."""
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        return task.result(), cancelled

    async def execute() -> None:
        nonlocal process

        async def start_process():
            from aion.capability_audit import job_started

            child = await asyncio.create_subprocess_exec(
                *argv, cwd=PROJECT_ROOT, env=environment.copy(),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            job_started()
            return child

        spawn = asyncio.create_task(start_process())
        try:
            process = await asyncio.shield(spawn)
        except asyncio.CancelledError:
            # The deadline and disconnect can arrive during startup. First
            # recover the process handle, then kill/reap it before returning.
            process, _ = await settle(spawn)
            readers = [asyncio.create_task(drain(process.stdout)), asyncio.create_task(drain(process.stderr))]
            await settle(asyncio.create_task(cleanup(process, readers)))
            raise

        readers = [asyncio.create_task(drain(process.stdout)), asyncio.create_task(drain(process.stderr))]
        try:
            await process.wait()
        finally:
            _, cancelled = await settle(asyncio.create_task(cleanup(process, readers)))
            if cancelled:
                raise asyncio.CancelledError

    status = "failed"
    try:
        # Cover startup as well as execution. Cleanup deliberately completes
        # before a timeout result or cancellation is delivered to the caller.
        async with asyncio.timeout(timeout_seconds):
            await execute()
        status = "succeeded" if process.returncode == 0 else "failed"
    except TimeoutError:
        status = "timeout"
    except OSError:
        status = "unavailable"

    result = {
        "ok": status == "succeeded", "job": job, "status": status,
        "exit_code": process.returncode if process else None,
        "arbitrary_commands_enabled": False,
    }
    if include_output:
        # Dropping incomplete/invalid UTF-8 preserves the retained byte limit;
        # replacement characters could expand a 12 KB byte buffer to 36 KB.
        result["output"] = output.decode("utf-8", errors="ignore")
        result["truncated"] = truncated
    if include_duration:
        result["duration_ms"] = int((time.monotonic() - started_at) * 1000)
    return result


async def run_validation() -> dict[str, Any]:
    """Validate runtime Python syntax; cancellation kills the entire process group."""
    return await run_fixed_job(
        argv=ARGV,
        timeout_seconds=TIMEOUT_SECONDS,
        environment=JOB_ENV,
        job="runtime.syntax",
        include_output=True,
    )
