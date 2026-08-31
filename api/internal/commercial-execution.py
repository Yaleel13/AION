"""Owner-only controlled commercial execution surface.

Preparation may create an exact-content approval request only for eligible public
Moltbook comment opportunities. Approval and execution remain separate owner
operations. Other commercial channels, grants, and federal bids are preparation-only.
"""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Request

from aion.commercial_execution import build_execution_plans, propose_commercial_execution
from aion.moltbook.execution import execute_approved_comment
from aion.moltbook.settings import load_moltbook_settings
from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _find_opportunity(svc, opportunity_id: str) -> dict:
    for row in svc.opportunity_store.top(limit=250):
        if str(row.get("opportunity_id") or "") == opportunity_id:
            return row
    raise HTTPException(status_code=404, detail="Opportunity not found")


def _snapshot(svc) -> dict:
    rows = svc.opportunity_store.top(limit=50)
    plans = build_execution_plans(rows, limit=25)
    executable = [plan for plan in plans if plan.get("executable")]
    return {
        "ok": True,
        "mode": "owner-controlled-commercial-execution",
        "plans": plans,
        "executable_count": len(executable),
        "preparation_only_count": len(plans) - len(executable),
        "outbound_enabled": load_moltbook_settings().outbound_enabled,
        "execute_enabled": load_moltbook_settings().execute_enabled,
        "grant_submission_enabled": False,
        "federal_bid_submission_enabled": False,
        "generic_external_send_enabled": False,
        "note": "Only eligible Moltbook public comments have a reviewed executor. Approval and execution are separate owner actions.",
    }


@app.get("/api/internal/commercial-execution")
async def commercial_execution_status(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    return _snapshot(get_services())


@app.post("/api/internal/commercial-execution")
async def commercial_execution_action(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    if svc.kill_switch.engaged:
        raise HTTPException(status_code=423, detail="Kill switch engaged")
    body = await request.json()
    operation = str(body.get("operation") or "prepare")

    if operation == "prepare":
        opportunity_id = str(body.get("opportunity_id") or "").strip()
        if not opportunity_id:
            raise HTTPException(status_code=400, detail="opportunity_id is required")
        row = _find_opportunity(svc, opportunity_id)
        try:
            proposed = propose_commercial_execution(row, svc.gate)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {**_snapshot(svc), "prepared": proposed}

    if operation == "approve":
        settings = load_moltbook_settings()
        if not settings.outbound_enabled:
            raise HTTPException(status_code=403, detail="MOLTBOOK_OUTBOUND_ENABLED is false")
        request_id = str(body.get("request_id") or "").strip()
        expected_hash = str(body.get("expected_content_hash") or "").strip()
        if not request_id:
            raise HTTPException(status_code=400, detail="request_id is required")
        approval = svc.gate.get(request_id)
        if approval is None or not approval.summary.startswith("Commercial pursuit reply for opportunity "):
            raise HTTPException(status_code=403, detail="Request is not a commercial pursuit approval")
        try:
            decided = svc.gate.decide(
                request_id,
                approved=True,
                decided_by="owner-boardroom",
                reason="owner explicitly approved exact commercial pursuit comment",
                expected_content_hash=expected_hash or None,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not decided.approval_token:
            raise HTTPException(status_code=500, detail="Approval token was not issued")
        return {
            **_snapshot(svc),
            "approved": decided.redacted(),
            "approval_token": decided.approval_token,
            "token_note": "Single-use token; execution is a separate owner action.",
        }

    if operation == "reject":
        request_id = str(body.get("request_id") or "").strip()
        if not request_id:
            raise HTTPException(status_code=400, detail="request_id is required")
        try:
            decided = svc.gate.decide(
                request_id,
                approved=False,
                decided_by="owner-boardroom",
                reason=str(body.get("reason") or "owner rejected commercial pursuit"),
                expected_content_hash=body.get("expected_content_hash"),
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {**_snapshot(svc), "rejected": decided.redacted()}

    if operation == "execute":
        settings = load_moltbook_settings()
        if not settings.outbound_enabled or not settings.execute_enabled:
            raise HTTPException(status_code=403, detail="Controlled execution requires both outbound and execute gates")
        request_id = str(body.get("request_id") or "").strip()
        approval_token = str(body.get("approval_token") or "").strip()
        if not request_id or not approval_token:
            raise HTTPException(status_code=400, detail="request_id and approval_token are required")
        approval = svc.gate.get(request_id)
        if approval is None or not approval.summary.startswith("Commercial pursuit reply for opportunity "):
            raise HTTPException(status_code=403, detail="Request is not a commercial pursuit approval")
        opportunity_id = approval.summary.removeprefix("Commercial pursuit reply for opportunity ").strip()
        try:
            result = await execute_approved_comment(
                svc.store,
                settings,
                request_id=request_id,
                approval_token=approval_token,
                token_pepper=svc.gate.token_pepper,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if result.get("published"):
            svc.opportunity_store.record_result(
                opportunity_id,
                result="owner_approved_outreach_sent",
                realized_value=0.0,
            )
        return {**_snapshot(svc), "execution": result, "opportunity_id": opportunity_id}

    if operation == "approve_and_execute":
        raise HTTPException(status_code=403, detail="Combined approve-and-execute is forbidden")

    raise HTTPException(status_code=400, detail="Unsupported operation")
