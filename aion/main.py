"""FastAPI application – entry point for the AION server."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from aion import config
from aion.agent_runtime import run_aion
from aion.moltbook.errors import MoltbookConfigError
from aion.moltbook.settings import load_moltbook_settings
from aion.schemas import (
    AIResponse,
    AgentRequest,
    AgentResponse,
    ChatGPTRequest,
    GeminiRequest,
)
from aion.services import query_chatgpt, query_gemini


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


@app.get("/health")
async def health() -> dict:
    """Health-check endpoint."""
    return {
        "status": "ok",
        "runtime": "agent-v1",
        "openai_configured": bool(config.OPENAI_API_KEY),
        "moltbook": _moltbook_health(),
    }


@app.post("/agent", response_model=AgentResponse, summary="Run AION")
async def agent_endpoint(request: AgentRequest) -> AgentResponse:
    """Run one turn through the primary AION agent orchestrator."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        result = await run_aion(request.message, request.session_id)
        return AgentResponse.model_validate(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/chatgpt", response_model=AIResponse, summary="Query ChatGPT (legacy)")
async def chatgpt_endpoint(request: ChatGPTRequest) -> AIResponse:
    """Forward a message to OpenAI ChatGPT and return the response."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        return await query_chatgpt(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/gemini", response_model=AIResponse, summary="Query Gemini (legacy)")
async def gemini_endpoint(request: GeminiRequest) -> AIResponse:
    """Forward a message to Google Gemini and return the response."""
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    try:
        return await query_gemini(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    except (MoltbookOutboundDisabledError, KeyError, Exception) as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Still do not call Moltbook write APIs here without an additional explicit
    # publish implementation review. Token is consumed to prevent replay.
    return {
        "consumed": True,
        "request": req.redacted(),
        "published": False,
        "note": "Token consumed; network publish not performed in this build.",
    }


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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
