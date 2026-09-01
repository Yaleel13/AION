#!/usr/bin/env python3
"""Export the canonical FastAPI OpenAPI schema for contract checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aion.main import app  # noqa: E402


def main() -> int:
    output = ROOT / "openapi" / "aion.openapi.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
