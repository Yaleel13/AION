"""Protected Vercel Cron entrypoint for automated payment order fulfillment."""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.fulfillment import fulfill_paid_orders
from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()


@app.get("/api/cron/fulfillment")
async def scheduled_fulfillment(authorization: str | None = Header(default=None)) -> dict:
    """
    Automatically fulfill all paid payment orders.
    
    Protected by CRON_SECRET bearer token.
    Requires FULFILLMENT_CRON_ENABLED=true to execute.
    Skipped if kill switch is engaged.
    
    Returns summary of processed orders with status and amounts.
    """
    secret = (os.getenv("CRON_SECRET") or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")

    expected = f"Bearer {secret}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

    enabled = (os.getenv("FULFILLMENT_CRON_ENABLED") or "false").lower() == "true"
    if not enabled:
        return {
            "ok": True,
            "scheduled": False,
            "reason": "FULFILLMENT_CRON_ENABLED is not set to true",
            "orders_processed": 0,
        }

    reset_services_cache()
    svc = get_services()

    if svc.kill_switch.engaged:
        return {
            "ok": True,
            "scheduled": False,
            "reason": f"Kill switch engaged: {svc.kill_switch.reason}",
            "orders_processed": 0,
        }

    try:
        order_ids = fulfill_paid_orders(svc.opportunity_store)
        return {
            "ok": True,
            "scheduled": True,
            "orders_processed": len(order_ids),
            "order_ids": order_ids,
            "note": f"Successfully fulfilled {len(order_ids)} payment order(s)",
        }
    except Exception as exc:
        return {
            "ok": False,
            "scheduled": False,
            "error": str(exc),
            "orders_processed": 0,
        }
