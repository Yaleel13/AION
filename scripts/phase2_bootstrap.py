#!/usr/bin/env python3
"""Bootstrap Phase 2 local state: drafts, paper tick, optional lead scan.

Does not publish, comment, follow, message, or place live trades.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AION_PHASE2_DB", "/tmp/aion_phase2.db")
os.environ.setdefault("AION_PAPER_DB", "/tmp/aion_paper_trading.db")
os.environ.setdefault("AION_PAPER_PRICE_MODE", "mock")
os.environ.setdefault("MOLTBOOK_MODE", "mock")

from aion.phase2_services import dashboard_snapshot, get_services, reset_services_cache


def main() -> int:
    reset_services_cache()
    svc = get_services()
    created = svc.drafts.seed_fourteen_day_campaign()
    paper = svc.paper.run_starter_strategy_once()
    snap = dashboard_snapshot()
    print(
        json.dumps(
            {
                "drafts_seeded": len(created),
                "published": False,
                "paper_equity": paper["mark"]["equity"],
                "kill_switch": snap["kill_switch"],
                "pending_approvals": len(snap["approvals_pending"]),
                "note": "Drafts only. No outbound publish performed.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
