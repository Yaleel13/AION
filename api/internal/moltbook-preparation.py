"""Stage 3 owner-token research preparation.

Transforms already-persisted Stage 2 leads into owner-review briefs only.
No Moltbook network writes are performed. Prepared state is stored in existing
risk_state so no schema change is required.
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()
KEY = "moltbook_stage3_preparation"
MAX_PREPARED = 8
MIN_STAGE3_CONFIDENCE = 0.70


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _is_actionable(lead: dict) -> bool:
    confidence = float(lead.get("confidence_score") or 0)
    risks = str(lead.get("risks") or "").lower()
    return confidence >= MIN_STAGE3_CONFIDENCE and "possible-help signal" not in risks


def _build_brief(leads: list[dict]) -> dict:
    actionable = [lead for lead in leads if _is_actionable(lead)]
    ranked = sorted(
        actionable,
        key=lambda x: (float(x.get("confidence_score") or 0), float(x.get("fit_score") or 0)),
        reverse=True,
    )
    items = []
    for lead in ranked[:MAX_PREPARED]:
        items.append({
            "lead_id": lead.get("lead_id"),
            "source_url": lead.get("source_url"),
            "requester_identity": lead.get("requester_identity"),
            "problem": lead.get("stated_problem"),
            "service": lead.get("relevant_service"),
            "fit_score": lead.get("fit_score"),
            "confidence_score": lead.get("confidence_score"),
            "response_draft": lead.get("suggested_response"),
            "risks": lead.get("risks"),
            "status": "owner_review_only",
            "untrusted_external_content": True,
        })
    return {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "stage": 3,
        "mode": "owner-review-preparation",
        "source_lead_count": len(leads),
        "actionable_lead_count": len(actionable),
        "prepared_count": len(items),
        "preparation_limit": MAX_PREPARED,
        "minimum_stage3_confidence": MIN_STAGE3_CONFIDENCE,
        "requires_explicit_need_signal": True,
        "items": items,
        "summary": (
            "No high-confidence explicit-need Stage 2 opportunities are currently stored; nothing was fabricated."
            if not items else f"Prepared {len(items)} high-confidence explicit-need owner-review opportunity brief(s)."
        ),
        "contacted": False,
        "published": False,
        "outbound_enabled": False,
    }


@app.get("/api/internal/moltbook-preparation")
async def get_preparation(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    return svc.store.get_risk(KEY) or _build_brief(svc.store.list_leads())


@app.post("/api/internal/moltbook-preparation")
async def prepare(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    brief = _build_brief(svc.store.list_leads())
    svc.store.set_risk(KEY, brief)
    svc.store.append_audit(
        module="moltbook",
        action="prepare_owner_review",
        success=True,
        detail={
            "source_leads": brief["source_lead_count"],
            "actionable_leads": brief["actionable_lead_count"],
            "prepared": brief["prepared_count"],
            "preparation_limit": brief["preparation_limit"],
            "published": False,
        },
    )
    return brief
