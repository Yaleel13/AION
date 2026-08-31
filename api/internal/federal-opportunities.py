"""Owner-only read/scan endpoint for federal grants and contract opportunities."""

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


@app.get("/api/internal/federal-opportunities")
async def list_federal_opportunities(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    ranked = svc.opportunity_store.top(limit=50)
    federal = [
        row for row in ranked
        if "grants.gov" in str(row.get("source") or "")
        or "sam.gov" in str(row.get("source") or "")
        or str(row.get("customer_problem") or "").startswith(("Grant opportunity:", "Federal contract opportunity:"))
    ]
    return {
        "ok": True,
        "opportunities": federal,
        "count": len(federal),
        "sam_configured": bool((os.getenv("SAM_GOV_API_KEY") or "").strip()),
        "outbound_enabled": False,
        "application_or_bid_authority": False,
    }


@app.post("/api/internal/federal-opportunities")
async def scan_federal_opportunities(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    if svc.kill_switch.engaged:
        raise HTTPException(status_code=423, detail="Kill switch engaged")
    result = await svc.scan_federal_opportunities()
    ranked = svc.opportunity_store.top(limit=25)
    return {
        "ok": True,
        "scan": result,
        "ranked_count": len(ranked),
        "highest_probability_legitimate_action": ranked[0] if ranked else None,
        "outbound_enabled": False,
        "application_or_bid_authority": False,
        "transaction_authority": False,
    }
