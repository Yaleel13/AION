"""Owner-only pursuit packet endpoint.

Returns preparation materials for qualified opportunities. This endpoint never
sends, submits, bids, applies, registers, or transacts.
"""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Query

from aion.opportunity_qualification import qualify_ranked
from aion.phase2_services import get_services, reset_services_cache
from aion.pursuit_packets import build_top_packets

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    expected = f"Bearer {token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/internal/pursuit-packets")
async def pursuit_packets(
    authorization: str | None = Header(default=None),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    rows = qualify_ranked(svc.opportunity_store.top(limit=50))
    packets = build_top_packets(rows, limit=limit)
    return {
        "ok": True,
        "packets": packets,
        "count": len(packets),
        "send_or_submit_enabled": False,
        "owner_approval_required": True,
    }
