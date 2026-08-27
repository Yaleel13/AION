"""Owner-token Moltbook research endpoint for Stage 2.

Read-only against Moltbook. POST scans the live public feed and persists
qualified opportunities through the existing Phase2Store. GET returns the
stored owner review queue. No outbound action is executed here.
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


def _owner_view(row: dict) -> dict:
    return {
        "lead_id": row.get("lead_id"),
        "source_url": row.get("source_url"),
        "requester_identity": row.get("requester_identity"),
        "stated_problem": row.get("stated_problem"),
        "relevant_service": row.get("relevant_service"),
        "fit_score": row.get("fit_score"),
        "confidence_score": row.get("confidence_score"),
        "suggested_response": row.get("suggested_response"),
        "risks": row.get("risks"),
        "approval_status": row.get("approval_status"),
        "conversion_outcome": row.get("conversion_outcome"),
        "created_at": row.get("created_at"),
        "untrusted_external_content": True,
    }


@app.get("/api/internal/moltbook-research")
async def list_research(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    leads = [_owner_view(row) for row in svc.store.list_leads()[:50]]
    return {
        "ok": True,
        "stage": 2,
        "mode": "live-read-only",
        "leads": leads,
        "count": len(leads),
        "contacted": False,
        "outbound_enabled": False,
    }


@app.post("/api/internal/moltbook-research")
async def scan_research(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    if svc.kill_switch.engaged:
        raise HTTPException(status_code=423, detail="Kill switch engaged")

    discovered = await svc.leads().scan_feed(limit=40)
    stored = svc.store.list_leads()
    return {
        "ok": True,
        "stage": 2,
        "mode": "live-read-only",
        "scanned_limit": 40,
        "qualified_this_scan": len(discovered),
        "stored_count": len(stored),
        "leads": [_owner_view(row) for row in stored[:50]],
        "contacted": False,
        "outbound_enabled": False,
        "execute_enabled": False,
    }
