"""Protected Vercel Cron entrypoint for AION's safe operations cycle."""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.durable.db import storage_status
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
    # No queued comments or campaign posts are published by this cron.
    result = await run_cycle(flush_queue=False, publish_next_draft=False)
    return {"ok": True, "scheduled": True, "result": result}
