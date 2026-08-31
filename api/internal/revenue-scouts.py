"""Owner-only external revenue scout endpoint.

POST performs read-only scans of allowlisted public JSON sources. GET returns the
current unified Opportunity Ledger. No outreach or transaction is executed.
"""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    expected = f"Bearer {token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/internal/revenue-scouts")
async def list_opportunities(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    opportunities = svc.opportunity_store.top(limit=50)
    return {
        "ok": True,
        "mode": "read-only-discovery",
        "opportunities": opportunities,
        "count": len(opportunities),
        "highest_probability_legitimate_action": opportunities[0] if opportunities else None,
        "outbound_enabled": False,
        "transaction_authority": False,
    }


@app.post("/api/internal/revenue-scouts")
async def scan_opportunities(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    if svc.kill_switch.engaged:
        raise HTTPException(status_code=423, detail="Kill switch engaged")

    scan = await svc.scan_external_opportunities()
    opportunities = svc.opportunity_store.top(limit=50)
    return {
        "ok": True,
        "mode": "live-public-read-only",
        "promoted_this_scan": scan["promoted_count"],
        "errors": scan["errors"],
        "opportunities": opportunities,
        "count": len(opportunities),
        "highest_probability_legitimate_action": opportunities[0] if opportunities else None,
        "outbound_enabled": False,
        "transaction_authority": False,
    }
