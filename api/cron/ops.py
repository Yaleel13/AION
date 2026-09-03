"""Protected Vercel Cron entrypoint for AION's safe operations cycle.

Live outbound / execute gates are controlled exclusively by environment
variables (MOLTBOOK_OUTBOUND_ENABLED, MOLTBOOK_EXECUTE_ENABLED,
MOLTBOOK_CONTROLLED_AUTONOMY) set in the Vercel project dashboard after
explicit owner review.  A time-bounded in-process activation window was
present here previously and has been removed; all such activations now
require an owner to set the relevant env vars directly.
"""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.durable.db import storage_status
from aion.phase2_services import get_services, reset_services_cache
from scripts.experiment_ops_cycle import run_cycle

app = FastAPI()


@app.get("/api/cron/revenue-ops")
@app.get("/api/cron/ops")
async def scheduled_ops(
    authorization: str | None = Header(default=None),
) -> dict:
    secret = (os.getenv("CRON_SECRET") or "").strip()
    expected = f"Bearer {secret}" if secret else ""
    cron_authorized = bool(
        expected and authorization and hmac.compare_digest(authorization, expected)
    )
    if not cron_authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")

    storage = storage_status()
    if not storage.configured or storage.backend != "postgres":
        raise HTTPException(
            status_code=503,
            detail="Durable Postgres storage is required before scheduled ops can run",
        )

    # Outbound / execute gates are read from env vars set by the owner in
    # the Vercel project; no in-process override is applied here.
    outbound_enabled = (os.getenv("MOLTBOOK_OUTBOUND_ENABLED") or "false").lower() in {"1", "true", "yes"}

    reset_services_cache()
    svc = get_services()
    revenue_scans: dict = {}
    if svc.kill_switch.engaged:
        revenue_scans = {"skipped": "kill_switch_engaged"}
    else:
        # Scan public sources before the ops cycle so Reddit/GitHub/HN hits can
        # be promoted to leads and selected as conversion candidates this run.
        revenue_scans["external"] = await svc.scan_external_opportunities()
        revenue_scans["federal"] = await svc.scan_federal_opportunities()
        ranked = svc.opportunity_store.top(limit=25)
        revenue_scans["ranked_count"] = len(ranked)
        revenue_scans["highest_probability_legitimate_action"] = ranked[0] if ranked else None

    result = await run_cycle(
        flush_queue=outbound_enabled,
        publish_next_draft=outbound_enabled,
    )

    return {
        "ok": True,
        "scheduled": cron_authorized,
        "result": result,
        "revenue_scans": revenue_scans,
        "outbound_enabled": bool(outbound_enabled and not svc.kill_switch.engaged),
        "application_or_bid_authority": False,
        "transaction_authority": False,
    }
