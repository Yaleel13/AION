#!/usr/bin/env python3
"""Regenerate and diff the committed FastAPI OpenAPI contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "openapi" / "aion.openapi.json"


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_openapi.py")], check=True)
    generated = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if not CONTRACT.exists():
        print("Missing openapi/aion.openapi.json after generation", file=sys.stderr)
        return 1
    # Re-read to ensure file on disk matches generated object shape.
    committed = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if generated != committed:
        print("OpenAPI contract is out of date. Run: python scripts/generate_openapi.py", file=sys.stderr)
        return 1
    print("OpenAPI contract is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
