"""Owner-only qualified buyer sales queue.

GET returns a conversion-oriented view of high-confidence leads. POST may prepare
an attributable Stripe Checkout Session for a selected lead/product pair, but
never charges the buyer or publishes outreach.
"""

from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from aion.phase2_services import get_services, reset_services_cache
from aion.revenue.lead_checkout import prepare_lead_checkout
from aion.revenue.product_catalog import match_product_for_lead

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    expected = f"Bearer {token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _lead_by_id(svc: Any, lead_id: str) -> dict[str, Any]:
    for lead in svc.store.list_leads():
        if str(lead.get("lead_id") or "") == lead_id:
            return lead
    raise HTTPException(status_code=404, detail="Lead not found")


def _sales_queue(svc: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lead in svc.store.list_leads():
        confidence = float(lead.get("confidence_score") or 0)
        if confidence < 0.7:
            continue
        product = match_product_for_lead(lead)
        rows.append(
            {
                "lead_id": lead.get("lead_id"),
                "confidence": confidence,
                "service": lead.get("relevant_service"),
                "problem": lead.get("stated_problem") or lead.get("raw_excerpt"),
                "requester": lead.get("requester_identity"),
                "source_url": lead.get("source_url"),
                "source_post_id": lead.get("source_post_id"),
                "suggested_response": lead.get("suggested_response"),
                "approval_status": lead.get("approval_status"),
                "matched_venture": product.venture,
                "matched_product": product.name,
                "matched_product_key": product.product_key,
                "sale_status": product.sale_status,
                "shared_checkout_url": product.checkout_url,
                "next_action": "prepare_attributed_checkout" if product.checkout_url else "review_offer_readiness",
            }
        )
    rows.sort(key=lambda item: float(item.get("confidence") or 0), reverse=True)
    return rows[:25]


@app.get("/api/internal/sales-alerts")
async def list_sales_alerts(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    queue = _sales_queue(svc)
    return {
        "ok": True,
        "mode": "owner-qualified-buyer-sales-queue",
        "count": len(queue),
        "highest_priority": queue[0] if queue else None,
        "sales_queue": queue,
        "checkout_creation_charges_buyer": False,
        "outreach_published_by_this_endpoint": False,
    }


@app.post("/api/internal/sales-alerts")
async def sales_alert_action(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    if svc.kill_switch.engaged:
        raise HTTPException(status_code=423, detail="Kill switch engaged")

    body = await request.json()
    operation = str(body.get("operation") or "").strip()
    if operation != "prepare_checkout":
        raise HTTPException(status_code=400, detail="Unsupported operation")

    lead_id = str(body.get("lead_id") or "").strip()
    if not lead_id:
        raise HTTPException(status_code=400, detail="lead_id is required")
    lead = _lead_by_id(svc, lead_id)
    if float(lead.get("confidence_score") or 0) < 0.7:
        raise HTTPException(status_code=400, detail="Lead is below qualified buyer threshold")

    product = match_product_for_lead(lead)
    checkout = prepare_lead_checkout(
        lead=lead,
        product=product,
        store=svc.opportunity_store,
    )
    return {
        "ok": True,
        "lead_id": lead_id,
        "product": {
            "venture": product.venture,
            "name": product.name,
            "product_key": product.product_key,
            "sale_status": product.sale_status,
        },
        "checkout": checkout,
        "suggested_response": lead.get("suggested_response"),
        "source_url": lead.get("source_url"),
        "note": "Checkout creation is attributable preparation only; the buyer must explicitly complete payment.",
    }
