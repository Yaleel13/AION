#!/usr/bin/env python3
"""Generate AION_OWNER_TOKEN and write it into local .env (never print full token).

Usage:
  python3 scripts/generate_owner_token.py
  python3 scripts/generate_owner_token.py --show-fingerprint-only
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aion.owner_alerts import generate_owner_token, owner_token_fingerprint


def upsert_env(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    line = f"{key}={value}"
    if pattern.search(text):
        text = pattern.sub(line, text)
    else:
        text = text.rstrip() + f"\n\n# Generated locally — never commit\n{line}\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument(
        "--show-fingerprint-only",
        action="store_true",
        help="Do not rotate; print fingerprint of existing token",
    )
    args = parser.parse_args()
    env_path = Path(args.env_file)

    if args.show_fingerprint_only:
        raw = ""
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("AION_OWNER_TOKEN="):
                    raw = line.split("=", 1)[1].strip()
        if not raw:
            print("AION_OWNER_TOKEN not set")
            return 1
        print(f"fingerprint={owner_token_fingerprint(raw)}")
        return 0

    token = generate_owner_token()
    upsert_env(env_path, "AION_OWNER_TOKEN", token)
    # Also set a fresh approval pepper if missing/placeholder
    pepper_needed = True
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("AION_APPROVAL_TOKEN_PEPPER="):
                val = line.split("=", 1)[1].strip()
                if val and not val.startswith("change-me"):
                    pepper_needed = False
    if pepper_needed:
        upsert_env(env_path, "AION_APPROVAL_TOKEN_PEPPER", generate_owner_token(nbytes=24))

    print(f"wrote AION_OWNER_TOKEN to {env_path} fingerprint={owner_token_fingerprint(token)}")
    print("Token value not printed. Store only as server-side secret.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
