#!/usr/bin/env python3
"""Migrate ephemeral /tmp AION SQLite state into durable AION_DATA_DIR.

Usage:
  python3 scripts/migrate_durable_storage.py
  python3 scripts/migrate_durable_storage.py --dry-run
  python3 scripts/migrate_durable_storage.py --rollback data/aion/migration_backups/<ts>

Does not reset quotas. Refuses to overwrite a larger destination DB.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aion.durable.migrate import migrate_to_durable, rollback_from_backup
from aion.durable.paths import resolve_durable_paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", type=str, default="", help="Backup dir to restore")
    parser.add_argument("--phase2-source", type=str, default="")
    parser.add_argument("--paper-source", type=str, default="")
    parser.add_argument("--activation-source", type=str, default="")
    args = parser.parse_args()

    paths = resolve_durable_paths()
    if args.rollback:
        result = rollback_from_backup(args.rollback, paths=paths)
        print(json.dumps(result, indent=2))
        return 0

    report = migrate_to_durable(
        paths=paths,
        phase2_source=args.phase2_source or None,
        paper_source=args.paper_source or None,
        activation_source=args.activation_source or None,
        dry_run=args.dry_run,
    )
    print(json.dumps(report.to_dict(), indent=2))
    if report.warnings and not report.quota_counts and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
