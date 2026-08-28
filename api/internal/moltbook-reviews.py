"""Owner-only quality feedback for Moltbook opportunity review.

Persists owner dispositions in existing durable risk_state and audit tables.
No Moltbook network writes are performed.
"""
from __future__ import annotations

import hmac
import os
from collections import Counter
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request

from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()
KEY_PREFIX = "moltbook_opportunity_review:"
ALLOWED = {"strong_lead", "possible_lead", "informational", "wrong_service", "noise"}
POSITIVE = {"strong_lead", "possible_lead"}


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _snapshot(svc) -> dict:
    records = svc.store.list_risk_prefix(KEY_PREFIX)
    reviews = []
    for row in records:
        value = dict(row.get("value") or {})
        value.setdefault("updated_at", row.get("updated_at"))
        reviews.append(value)
    counts = Counter(str(item.get("disposition") or "") for item in reviews)
    reviewed = len(reviews)
    positive = sum(counts[name] for name in POSITIVE)
    precision = (positive / reviewed) if reviewed else None
    return {
        "ok": True,
        "mode": "owner-quality-feedback",
        "reviewed_count": reviewed,
        "positive_count": positive,
        "precision": precision,
        "target_precision": 0.70,
        "counts": {name: counts[name] for name in sorted(ALLOWED)},
        "reviews": reviews[:100],
        "outbound_enabled": False,
        "published": False,
    }


@app.get("/api/internal/moltbook-reviews")
async def get_reviews(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    return _snapshot(get_services())


@app.post("/api/internal/moltbook-reviews")
async def set_review(request: Request, authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    body = await request.json()
    lead_id = str(body.get("lead_id") or "").strip()
    disposition = str(body.get("disposition") or "").strip()
    if not lead_id:
        raise HTTPException(status_code=400, detail="lead_id is required")
    if disposition not in ALLOWED:
        raise HTTPException(status_code=400, detail="Unsupported disposition")
    known_ids = {str(item.get("lead_id") or "") for item in svc.store.list_leads()}
    if lead_id not in known_ids:
        raise HTTPException(status_code=404, detail="Lead not found")
    record = {
        "lead_id": lead_id,
        "disposition": disposition,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": "owner-boardroom",
    }
    svc.store.set_risk(f"{KEY_PREFIX}{lead_id}", record)
    svc.store.append_audit(
        module="moltbook",
        action="owner_opportunity_disposition",
        success=True,
        detail={"lead_id": lead_id, "disposition": disposition, "published": False},
    )
    return {**_snapshot(svc), "updated": record}
