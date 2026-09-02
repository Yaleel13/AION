"""Protected Vercel Cron entrypoint for AION's safe operations cycle."""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query

from aion.durable.db import storage_status
from aion.phase2_services import get_services, reset_services_cache
from scripts.experiment_ops_cycle import run_cycle

app = FastAPI()

REVENUE_WINDOW_START = datetime.fromisoformat("2026-09-02T14:06:14+00:00")
REVENUE_WINDOW_END = datetime.fromisoformat("2026-09-02T20:06:14+00:00")
# SHA-256 only; the activation token itself is never stored in source control.
REVENUE_WINDOW_ACTIVATION_TOKEN_SHA256 = "2878c6c8e6f9a506beb4efca3cb2c5d28d701091338eb5d7ead29c8b3b1e1e7a"


def _six_hour_window_active() -> bool:
    now = datetime.now(timezone.utc)
    return REVENUE_WINDOW_START <= now < REVENUE_WINDOW_END


def _manual_activation_authorized(token: str | None) -> bool:
    if not token or not _six_hour_window_active():
        return False
    supplied = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(supplied, REVENUE_WINDOW_ACTIVATION_TOKEN_SHA256)


def _apply_revenue_window_runtime_flags(active: bool) -> None:
    """Apply the owner's time-bounded activation only inside this cron process.

    This never changes the kill switch, credentials, Stripe payout settings, or
    any persistent secret. Outside the six-hour window all live Moltbook gates
    are explicitly returned to their fail-closed values.
    """
    if active:
        os.environ["MOLTBOOK_OUTBOUND_ENABLED"] = "true"
        os.environ["MOLTBOOK_EXECUTE_ENABLED"] = "true"
        os.environ["MOLTBOOK_CONTROLLED_AUTONOMY"] = "true"
        os.environ["MOLTBOOK_AUTONOMY_DRY_RUN"] = "false"
        os.environ["MOLTBOOK_EXPERIMENT_STARTED_AT"] = REVENUE_WINDOW_START.isoformat()
    else:
        os.environ["MOLTBOOK_OUTBOUND_ENABLED"] = "false"
        os.environ["MOLTBOOK_EXECUTE_ENABLED"] = "false"
        os.environ["MOLTBOOK_CONTROLLED_AUTONOMY"] = "false"
        os.environ["MOLTBOOK_AUTONOMY_DRY_RUN"] = "true"


@app.get("/api/cron/ops")
async def scheduled_ops(
    authorization: str | None = Header(default=None),
    activation: str | None = Query(default=None, include_in_schema=False),
) -> dict:
    secret = (os.getenv("CRON_SECRET") or "").strip()
    expected = f"Bearer {secret}" if secret else ""
    cron_authorized = bool(
        expected and authorization and hmac.compare_digest(authorization, expected)
    )
    manual_authorized = _manual_activation_authorized(activation)
    if not cron_authorized and not manual_authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")

    storage = storage_status()
    if not storage.configured or storage.backend != "postgres":
        raise HTTPException(
            status_code=503,
            detail="Durable Postgres storage is required before scheduled ops can run",
        )

    six_hour_active = _six_hour_window_active()
    _apply_revenue_window_runtime_flags(six_hour_active)

    # During the owner-authorized six-hour revenue window, controlled autonomy
    # may flush qualified queued comments and publish the next qualified draft.
    # All existing policy, pacing, secret/PII scanning, kill-switch, and
    # automatic read-only fallback protections remain in force.
    result = await run_cycle(
        flush_queue=six_hour_active,
        publish_next_draft=six_hour_active,
    )

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
        "scheduled": cron_authorized,
        "manual_activation": manual_authorized,
        "six_hour_revenue_window": {
            "active": six_hour_active,
            "started_at": REVENUE_WINDOW_START.isoformat(),
            "expires_at": REVENUE_WINDOW_END.isoformat(),
        },
        "result": result,
        "revenue_scans": revenue_scans,
        "outbound_enabled": bool(six_hour_active and not svc.kill_switch.engaged),
        "application_or_bid_authority": False,
        "transaction_authority": False,
    }
