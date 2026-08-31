"""Protected Vercel Cron entrypoint for AION's safe operations cycle."""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.durable.db import storage_status
from aion.phase2_services import get_services, reset_services_cache
from scripts.experiment_ops_cycle import run_cycle

app = FastAPI()


@app.get("/api/cron/ops")
async def scheduled_ops(authorization: str | None = Header(default=None)) -> dict:
    secret = (os.getenv("CRON_SECRET") or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")

    expected = f"Bearer {secret}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

    storage = storage_status()
    if not storage.configured or storage.backend != "postgres":
        raise HTTPException(
            status_code=503,
            detail="Durable Postgres storage is required before scheduled ops can run",
        )

    # Safe scheduled cycle: research, drafts, paper-only tick, leads, daily report.
    # No queued comments, campaign posts, applications, bids, or transactions are executed.
    result = await run_cycle(flush_queue=False, publish_next_draft=False)

    reset_services_cache()
    svc = get_services()
    revenue_scans: dict = {}
    if svc.kill_switch.engaged:
        revenue_scans = {"skipped": "kill_switch_engaged"}
    else:
        revenue_scans["external"] = await svc.scan_external_opportunities()
        revenue_scans["federal"] = await svc.scan_federal_opportunities()
        ranked = svc.opportunity_store.top(limit=25)
        revenue_scans["ranked_count"] = len(ranked)
        revenue_scans["highest_probability_legitimate_action"] = ranked[0] if ranked else None

    return {
        "ok": True,
        "scheduled": True,
        "result": result,
        "revenue_scans": revenue_scans,
        "outbound_enabled": False,
        "application_or_bid_authority": False,
        "transaction_authority": False,
    }
