"""FastAPI application – entry point for the AION server."""

from contextlib import asynccontextmanager
import math

from fastapi import FastAPI, HTTPException, Request

from aion import config
from aion.agent_runtime import run_aion
from aion.moltbook.errors import MoltbookConfigError
from aion.moltbook.settings import load_moltbook_settings
from aion.rate_limit import ClientSlidingWindowRateLimiter, RateLimitExceeded
from aion.schemas import (
    AIResponse,
    AgentRequest,
    AgentResponse,
    ChatGPTRequest,
    GeminiRequest,
)
from aion.http_errors import owner_request_error, upstream_provider_error
from aion.opportunity_store import OpportunityStore
from aion.services import query_chatgpt, query_gemini
from aion.stripe_runtime import StripeRuntime


def _moltbook_health() -> dict:
    """Report Moltbook integration status without exposing secrets."""
    try:
        settings = load_moltbook_settings()
    except MoltbookConfigError as exc:
        return {
            "configured": False,
            "mode": None,
            "outbound_enabled": False,
            "phase": "phase2-controlled-growth",
            "error": str(exc),
        }
    return {
        "configured": settings.is_mock or settings.configured_for_live,
        "mode": settings.mode,
        "api_key_present": bool(settings.api_key),
        "outbound_enabled": False,
        "phase": "phase2-controlled-growth",
        "execute_enabled": False,
        "controlled_autonomy_default": "inactive",
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate optional Moltbook settings without failing closed on misconfig."""
    try:
        load_moltbook_settings()
    except MoltbookConfigError:
        # Live callers fail closed on client create; health surfaces the error.
        pass
    yield


app = FastAPI(
    title="AION",
    description="The Alchemical Intelligence for Ontological Navigation.",
    version="0.2.0",
    lifespan=lifespan,
)
agent_rate_limiter = ClientSlidingWindowRateLimiter(
    max_requests=config.AGENT_RATE_LIMIT_PER_MINUTE
)


@app.get("/health")
async def health() -> dict:
    """Health-check endpoint."""
    return {
        "status": "ok",
        "runtime": "agent-v1",
        "openai_configured": bool(config.OPENAI_API_KEY),
        "moltbook": _moltbook_health(),
    }


@app.get("/runtime/status", summary="Truthful runtime status (no secrets)")
async def runtime_status() -> dict:
    """Real storage / Moltbook / autonomy / paper gates for UI honesty."""
    from aion.runtime_status import build_runtime_status

    return build_runtime_status()


@app.post("/agent", response_model=AgentResponse, summary="Run AION")
async def agent_endpoint(request: AgentRequest, http_request: Request) -> AgentResponse:
    """Run one turn through the primary AION agent orchestrator."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    client_id = http_request.client.host if http_request.client else "unknown"
    try:
        agent_rate_limiter.acquire(client_id)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(math.ceil(exc.retry_after_seconds))},
        ) from exc
    try:
        result = await run_aion(request.message, request.session_id)
        return AgentResponse.model_validate(result)
    except Exception as exc:
        raise upstream_provider_error(exc) from exc


@app.post("/chatgpt", response_model=AIResponse, summary="Query ChatGPT (legacy)")
async def chatgpt_endpoint(request: ChatGPTRequest) -> AIResponse:
    """Forward a message to OpenAI ChatGPT and return the response."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        return await query_chatgpt(request)
    except Exception as exc:
        raise upstream_provider_error(exc) from exc


@app.post("/gemini", response_model=AIResponse, summary="Query Gemini (legacy)")
async def gemini_endpoint(request: GeminiRequest) -> AIResponse:
    """Forward a message to Google Gemini and return the response."""
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    try:
        return await query_gemini(request)
    except Exception as exc:
        raise upstream_provider_error(exc) from exc


# ---------------------------------------------------------------------------
# Phase 2 owner dashboard API (local; requires AION_OWNER_TOKEN)
# ---------------------------------------------------------------------------

import os

from fastapi import Header

from aion.moltbook.errors import MoltbookOutboundDisabledError
from aion.moltbook.limits import QuotaExceededError
from aion.phase2_services import dashboard_snapshot, get_services


def _require_owner(authorization: str | None) -> None:
    expected = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="AION_OWNER_TOKEN is not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    provided = authorization.removeprefix("Bearer ").strip()
    if provided != expected:
        raise HTTPException(status_code=403, detail="Invalid owner token")


@app.get("/owner/dashboard", summary="Phase 2 owner dashboard snapshot")
async def owner_dashboard(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    return dashboard_snapshot()


@app.post("/owner/campaign/seed", summary="Seed 14-day draft campaign (no publish)")
async def owner_seed_campaign(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    svc = get_services()
    created = svc.drafts.seed_fourteen_day_campaign()
    return {"created": created, "published": False}


@app.post("/owner/drafts/{draft_id}/queue", summary="Queue one draft for approval")
async def owner_queue_draft(
    draft_id: str, authorization: str | None = Header(default=None)
) -> dict:
    _require_owner(authorization)
    svc = get_services()
    try:
        return svc.drafts.submit_draft_for_approval(draft_id)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/owner/approvals/{request_id}/decide", summary="Approve or reject a proposal")
async def owner_decide(
    request_id: str,
    body: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_owner(authorization)
    svc = get_services()
    approved = bool(body.get("approved"))
    try:
        req = svc.gate.decide(
            request_id,
            approved=approved,
            decided_by=str(body.get("decided_by") or "owner"),
            reason=body.get("reason"),
            expected_content_hash=body.get("expected_content_hash"),
        )
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc
    payload = req.redacted()
    # Return raw token once if newly approved (owner must store it securely).
    if req.approval_token:
        payload["approval_token"] = req.approval_token
        payload["token_note"] = (
            "Single-use token shown once. Execution still disabled unless a "
            "separate explicit publish command is issued."
        )
    return payload


@app.post("/owner/leads/scan", summary="Scan public feed for qualified leads")
async def owner_scan_leads(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    svc = get_services()
    leads = await svc.leads().scan_feed(limit=25)
    return {"qualified": leads, "contacted": False}


@app.post("/owner/paper/tick", summary="Run one paper-trading rebalance + mark")
async def owner_paper_tick(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    svc = get_services()
    if svc.kill_switch.engaged:
        raise HTTPException(status_code=423, detail="Kill switch engaged")
    result = svc.paper.run_starter_strategy_once()
    return result


@app.post("/owner/kill-switch", summary="Engage or release emergency kill switch")
async def owner_kill_switch(
    body: dict, authorization: str | None = Header(default=None)
) -> dict:
    _require_owner(authorization)
    svc = get_services()
    engage = bool(body.get("engage"))
    if engage:
        svc.kill_switch.engage(str(body.get("reason") or "owner engaged"))
    else:
        svc.kill_switch.release(decided_by=str(body.get("decided_by") or "owner"))
    svc.store.set_risk("kill_switch", svc.kill_switch.snapshot())
    svc.store.append_audit(
        module="risk",
        action="kill_switch",
        success=True,
        detail=svc.kill_switch.snapshot(),
    )
    return svc.kill_switch.snapshot()


@app.post("/owner/execute", summary="Execute approved outbound (disabled by default)")
async def owner_execute(
    body: dict, authorization: str | None = Header(default=None)
) -> dict:
    """Refuse execution unless MOLTBOOK_PHASE2_EXECUTE=true.

    Even then, requires a valid single-use approval token. This endpoint exists
    for controlled future use; Phase 2 implementation stops before publishing.
    """
    _require_owner(authorization)
    if (os.getenv("MOLTBOOK_PHASE2_EXECUTE") or "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                "Execution disabled. Set MOLTBOOK_PHASE2_EXECUTE=true only with "
                "explicit owner intent to publish, then call with approval token."
            ),
        )
    svc = get_services()
    try:
        req = svc.gate.consume_for_execution(
            str(body["request_id"]),
            approval_token=str(body["approval_token"]),
            payload=body["payload"],
            destination=str(body["destination"]),
        )
    except MoltbookOutboundDisabledError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc
    # Still do not call Moltbook write APIs here without an additional explicit
    # publish implementation review. Token is consumed to prevent replay.
    return {
        "consumed": True,
        "request": req.redacted(),
        "published": False,
        "note": "Token consumed; network publish not performed in this build.",
    }


@app.post("/owner/checkout/prepare", summary="Prepare a Stripe checkout session for an approved order")
async def owner_checkout_prepare(
    body: dict, authorization: str | None = Header(default=None)
) -> dict:
    _require_owner(authorization)
    if not (os.getenv("STRIPE_CHECKOUT_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=403, detail="Stripe checkout is disabled")

    runtime = StripeRuntime()
    if not runtime.is_ready_for_checkout():
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")

    order_id = str(body.get("order_id") or "").strip()
    opportunity_id = str(body.get("opportunity_id") or "").strip()
    amount_cents = int(body.get("amount_cents") or 0)
    currency = str(body.get("currency") or "usd")
    success_url = str(body.get("success_url") or "").strip()
    customer_email = str(body.get("customer_email") or "").strip()
    commercial_execution_id = str(body.get("commercial_execution_id") or "").strip()
    lead_id = str(body.get("lead_id") or "").strip()
    product_key = str(body.get("product_key") or "").strip()
    source_post_id = str(body.get("source_post_id") or "").strip()
    source_url = str(body.get("source_url") or "").strip()
    venture = str(body.get("venture") or "").strip()
    if not order_id or not opportunity_id or amount_cents <= 0 or not success_url:
        raise HTTPException(status_code=400, detail="order_id, opportunity_id, amount_cents, and success_url are required")

    store = OpportunityStore()
    order = store.record_payment_order(
        order_id=order_id,
        opportunity_id=opportunity_id,
        amount_cents=amount_cents,
        currency=currency,
        customer_email=customer_email,
        commercial_execution_id=commercial_execution_id,
    )

    checkout_info = {}
    try:
        session = runtime.create_checkout_session(
            amount_cents=amount_cents,
            currency=currency,
            success_url=success_url,
            order_id=order_id,
            opportunity_id=opportunity_id,
            customer_email=customer_email,
            commercial_execution_id=commercial_execution_id,
            lead_id=lead_id,
            product_key=product_key,
            source_post_id=source_post_id,
            source_url=source_url,
            venture=venture,
        )
        checkout_info = {
            "session_id": session["session_id"],
            "checkout_url": session["checkout_url"],
            "live": True,
            "attribution": {
                "commercial_execution_id": commercial_execution_id,
                "lead_id": lead_id,
                "product_key": product_key,
                "source_post_id": source_post_id,
                "source_url": source_url,
                "venture": venture,
            },
        }
        store._conn.execute(
            "UPDATE payment_orders SET stripe_session_id = ?, stripe_checkout_url = ? WHERE order_id = ?",
            (session["session_id"], session["checkout_url"], order_id),
        )
        store._conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Stripe checkout session creation failed") from exc

    return {"status": "ready", "order": order, "checkout": checkout_info}


@app.post("/owner/checkout/webhook", summary="Handle signed Stripe webhook events")
async def owner_checkout_webhook(
    request: Request,
) -> dict:
    runtime = StripeRuntime()
    if not runtime.is_ready_for_checkout():
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")

    payload = await request.body()
    header = request.headers.get("Stripe-Signature", "")
    if not runtime.verify_webhook_signature(payload, header):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event = __import__("json").loads(payload.decode("utf-8"))
    event_id = str(event.get("id") or "").strip()
    event_type = str(event.get("type") or "unknown")
    if event_type not in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        return {"status": "ignored", "event_type": event_type, "event_id": event_id}
    session = (event.get("data") or {}).get("object") or {}
    metadata = dict(session.get("metadata") or {})
    order_id = str(metadata.get("order_id") or "").strip()
    opportunity_id = str(metadata.get("opportunity_id") or "").strip()
    commercial_execution_id = str(metadata.get("commercial_execution_id") or "").strip()
    lead_id = str(metadata.get("lead_id") or "").strip()
    product_key = str(metadata.get("product_key") or "").strip()
    source_post_id = str(metadata.get("source_post_id") or "").strip()
    source_url = str(metadata.get("source_url") or "").strip()
    venture = str(metadata.get("venture") or "").strip()
    amount = int(session.get("amount_total") or 0)
    currency = str(session.get("currency") or "usd")
    customer_email = str((session.get("customer_details") or {}).get("email") or "")

    store = OpportunityStore()

    if event_id and store.idempotency_key_exists(event_id):
        return {
            "status": "duplicate",
            "event_id": event_id,
            "event_type": event_type,
            "note": "This webhook event has already been processed",
        }

    if order_id:
        store.record_payment_order(
            order_id=order_id,
            opportunity_id=opportunity_id or "unknown",
            amount_cents=amount,
            currency=currency,
            customer_email=customer_email,
            status="paid",
            idempotency_key=event_id,
            commercial_execution_id=commercial_execution_id,
        )
        store.record_result(
            opportunity_id or order_id,
            result="stripe_checkout_completed",
            realized_value=max(0.0, amount / 100.0),
        )

    return {
        "status": "processed",
        "event_type": event_type,
        "order_id": order_id,
        "amount_total": amount,
        "currency": currency,
        "attribution": {
            "opportunity_id": opportunity_id,
            "commercial_execution_id": commercial_execution_id,
            "lead_id": lead_id,
            "product_key": product_key,
            "source_post_id": source_post_id,
            "source_url": source_url,
            "venture": venture,
        },
    }


@app.post("/owner/fulfill/paid-orders", summary="Manually trigger fulfillment of all paid payment orders")
async def owner_fulfill_paid_orders(
    body: dict, authorization: str | None = Header(default=None)
) -> dict:
    _require_owner(authorization)
    store = OpportunityStore()
    try:
        from aion.fulfillment import fulfill_paid_orders

        results = fulfill_paid_orders(store)
        return {
            "status": "completed",
            "orders_processed": len(results),
            "results": results,
            "note": "Owner-triggered fulfillment; all paid orders marked as fulfilled and opportunities updated.",
        }
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc


@app.get("/owner/revenue/attributed", summary="Get revenue attributed to commercial executions")
async def owner_revenue_attributed(
    opportunity_id: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict:
    """Query revenue attributed to commercial executions.

    Returns list of attributions with:
    - commercial_execution_id: ID of execution that generated revenue
    - opportunity_id: Associated opportunity
    - fulfilled_amount_cents: Amount successfully fulfilled
    - total_amount_cents: Total payment amount
    - order_count: Number of orders attributed
    """
    _require_owner(authorization)
    store = OpportunityStore()
    try:
        results = store.get_revenue_by_execution(opportunity_id=opportunity_id or "")
        return {
            "status": "success",
            "attributions": results,
            "total_attributed": len(results),
            "note": "Revenue attributed to commercial executions; filtered by opportunity if provided.",
        }
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc


@app.post("/owner/fulfillment/scheduler/start", summary="Start automatic fulfillment scheduler")
async def owner_start_fulfillment_scheduler(
    authorization: str | None = Header(default=None),
) -> dict:
    """Start background scheduler for automatic order fulfillment.

    Scheduler is disabled by default. Set FULFILLMENT_SCHEDULER_ENABLED=true to enable.
    """
    _require_owner(authorization)
    try:
        from aion.fulfillment_scheduler import get_scheduler

        scheduler = get_scheduler()
        return scheduler.start()
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc


@app.post("/owner/fulfillment/scheduler/stop", summary="Stop automatic fulfillment scheduler")
async def owner_stop_fulfillment_scheduler(
    authorization: str | None = Header(default=None),
) -> dict:
    """Stop the background fulfillment scheduler."""
    _require_owner(authorization)
    try:
        from aion.fulfillment_scheduler import get_scheduler

        scheduler = get_scheduler()
        return scheduler.stop()
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc


@app.get("/owner/fulfillment/scheduler/status", summary="Get fulfillment scheduler status")
async def owner_fulfillment_scheduler_status(
    authorization: str | None = Header(default=None),
) -> dict:
    """Get current fulfillment scheduler status and configuration."""
    _require_owner(authorization)
    try:
        from aion.fulfillment_scheduler import get_scheduler

        scheduler = get_scheduler()
        return {
            "status": "success",
            "scheduler": scheduler.status(),
        }
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc


@app.get("/owner/autonomy/status", summary="Controlled autonomy status (default inactive)")
async def owner_autonomy_status(
    authorization: str | None = Header(default=None),
) -> dict:
    _require_owner(authorization)
    return get_services().autonomy.status()


@app.post("/owner/autonomy/daily-report", summary="Build today's autonomy daily report")
async def owner_autonomy_daily_report(
    authorization: str | None = Header(default=None),
) -> dict:
    _require_owner(authorization)
    return get_services().autonomy.build_daily_report()


@app.post(
    "/owner/autonomy/dry-run/post",
    summary="Rehearse a post under policy (requires active+dry_run; never live)",
)
async def owner_autonomy_dry_run_post(
    body: dict, authorization: str | None = Header(default=None)
) -> dict:
    """Policy rehearsal only. Refuses unless dry_run is true.

    Activation itself remains gated by MOLTBOOK_CONTROLLED_AUTONOMY and the
    experiment clock. This endpoint never flips dry_run off.
    """
    _require_owner(authorization)
    svc = get_services()
    if not svc.autonomy.dry_run:
        raise HTTPException(
            status_code=403,
            detail="Refusing: dry_run is false. Live autonomous writes need separate final approval.",
        )
    try:
        return await svc.autonomy.execute_post(
            submolt=str(body.get("submolt") or "general"),
            title=str(body.get("title") or ""),
            content=str(body.get("content") or ""),
            inbound_context=str(body.get("inbound_context") or ""),
            idempotency_key=body.get("idempotency_key"),
        )
    except MoltbookOutboundDisabledError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise owner_request_error(exc) from exc
