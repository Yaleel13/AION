"""Owner-only pursuit qualification endpoint for AION Revenue Engine."""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.opportunity_qualification import qualify_ranked
from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    expected = f"Bearer {token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/internal/opportunity-qualification")
async def opportunity_qualification(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    rows = qualify_ranked(svc.opportunity_store.top(limit=50))
    counts: dict[str, int] = {}
    for row in rows:
        recommendation = str((row.get("qualification") or {}).get("recommendation") or "unknown")
        counts[recommendation] = counts.get(recommendation, 0) + 1
    return {
        "ok": True,
        "count": len(rows),
        "recommendation_counts": counts,
        "highest_priority": rows[0] if rows else None,
        "opportunities": rows,
        "authority": "read_only_decision_support",
        "applications_enabled": False,
        "bids_enabled": False,
        "transactions_enabled": False,
    }
