"""One fixed local runtime test manifest with no caller-controlled inputs."""

from __future__ import annotations

import sys
import tempfile
from typing import Any

from aion.local_executor import PROJECT_ROOT
from aion.local_validation import run_fixed_job

ARGV = (sys.executable, "-I", str(PROJECT_ROOT / "scripts/validate_runtime_tests.py"))
TIMEOUT_SECONDS = 180
MANIFEST = (
    "tests/test_local_validation.py",
    "tests/test_syntax_dispatch.py",
    "tests/test_capability_audit.py",
)


async def run_runtime_tests() -> dict[str, Any]:
    """Run the server-defined runtime safety manifest without returning output."""
    with tempfile.TemporaryDirectory(prefix="aion-runtime-tests-") as temporary:
        result = await run_fixed_job(
            argv=ARGV,
            timeout_seconds=TIMEOUT_SECONDS,
            environment={
                "LANG": "C.UTF-8",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TMPDIR": temporary,
                "TMP": temporary,
                "TEMP": temporary,
            },
            job="runtime.tests",
            include_output=False,
            include_duration=True,
        )
    return {
        key: result[key]
        for key in ("ok", "job", "status", "duration_ms", "arbitrary_commands_enabled")
    }
