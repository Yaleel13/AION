"""Run AION's fixed local-runtime safety manifest."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = (
    "tests/test_local_validation.py",
    "tests/test_syntax_dispatch.py",
    "tests/test_capability_audit.py",
)

raise SystemExit(pytest.main([*MANIFEST, "-q", "-p", "no:cacheprovider"]))
