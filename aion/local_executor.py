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
- read/test/build capabilities only in v1
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_OUTPUT = 12_000
DEFAULT_TIMEOUT = 120
PROJECT_ROOT = Path(__file__).resolve().parent.parent


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
        argv=("python", "-m", "pytest", "tests/", "-q"),
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


def _trim(value: str) -> str:
    if len(value) <= MAX_OUTPUT:
        return value
    return value[:MAX_OUTPUT] + "\n…truncated"


def _executable_available(argv: tuple[str, ...]) -> bool:
    return bool(argv and shutil.which(argv[0]))


def local_executor_available() -> bool:
    """Return whether this process is running in an eligible local OS runtime."""
    mode = (os.getenv("AION_RUNTIME_MODE") or "").strip().lower()
    return mode == "local" and PROJECT_ROOT.exists()


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


def execute_capability(name: str) -> dict[str, Any]:
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

    if not _executable_available(capability.argv):
        return {
            "ok": False,
            "capability": name,
            "error": f"Required executable is unavailable: {capability.argv[0]}",
        }

    try:
        completed = subprocess.run(
            capability.argv,
            cwd=capability.cwd,
            capture_output=True,
            text=True,
            timeout=capability.timeout,
            check=False,
            shell=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "capability": name,
            "classification": capability.classification,
            "error": f"Capability timed out after {capability.timeout} seconds.",
            "stdout": _trim(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": _trim(exc.stderr or "") if isinstance(exc.stderr, str) else "",
        }
    except OSError as exc:
        return {
            "ok": False,
            "capability": name,
            "classification": capability.classification,
            "error": str(exc),
        }

    return {
        "ok": completed.returncode == 0,
        "executor": "aion-local-controlled",
        "mode": "local-controlled",
        "capability": capability.name,
        "classification": capability.classification,
        "exit_code": completed.returncode,
        "stdout": _trim(completed.stdout),
        "stderr": _trim(completed.stderr),
        "cwd": str(capability.cwd),
        "arbitrary_commands_enabled": False,
        "sudo_enabled": False,
    }
