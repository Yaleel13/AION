#!/usr/bin/env python3
"""Regenerate and diff the committed AION inventory manifest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "aion-inventory.yaml"


def _normalize(payload: dict) -> dict:
    normalized = dict(payload)
    normalized.pop("generated_at", None)
    return normalized


def main() -> int:
    if not CONTRACT.exists():
        print("Missing aion-inventory.yaml", file=sys.stderr)
        return 1
    committed = _normalize(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_inventory.py")], check=True)
    generated = _normalize(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))
    if committed != generated:
        print("Inventory manifest is out of date. Run: python scripts/generate_inventory.py", file=sys.stderr)
        return 1
    print("Inventory manifest is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
