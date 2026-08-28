"""Owner-controlled Moltbook approval and execution surface.

Proposal/rejection remain available with outbound disabled. Approval requires the
explicit outbound gate plus quality evidence. Execution is a separate operation
requiring a second environment gate and a single-use owner approval token.
"""
from __future__ import annotations

import hmac
import os
import re
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Request

from aion.moltbook.approval import OutboundAction
from aion.moltbook.execution import execute_approved_comment
from aion.moltbook.limits import QuotaExceededError
from aion.moltbook.settings import load_moltbook_settings
from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()
PREPARATION_KEY = "moltbook_stage3_preparation"
REVIEW_PREFIX = "moltbook_opportunity_review:"
POSITIVE_DISPOSITIONS = {"strong_lead", "possible_lead"}
MIN_QUALITY_REVIEWS = 5
MIN_QUALITY_PRECISION = 0.70


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _post_id_from_source(source_url: str) -> str:
    try:
        parts = [part for part in urlparse(source_url).path.split("/") if part]
    except Exception:
        return ""
    if "posts" in parts:
        index = parts.index("posts")
        if index + 1 < len(parts):
            return parts[index + 1]
    return parts[-1] if parts else ""


def _lead_id_from_summary(summary: str) -> str | None:
    match = re.search(r"lead ([0-9a-f-]{8,})", summary, flags=re.I)
    return match.group(1) if match else None


def _quality_snapshot(svc) -> dict:
    records = svc.store.list_risk_prefix(REVIEW_PREFIX)
    dispositions = [str((row.get("value") or {}).get("disposition") or "") for row in records]
    reviewed = len(dispositions)
    positive = sum(1 for value in dispositions if value in POSITIVE_DISPOSITIONS)
    precision = (positive / reviewed) if reviewed else None
    return {
        "reviewed_count": reviewed,
        "positive_count": positive,
        "precision": precision,
        "minimum_reviews": MIN_QUALITY_REVIEWS,
        "minimum_precision": MIN_QUALITY_PRECISION,
        "ready": reviewed >= MIN_QUALITY_REVIEWS and precision is not None and precision >= MIN_QUALITY_PRECISION,
    }


def _lead_disposition(svc, lead_id: str) -> str | None:
    row = svc.store.get_risk(f"{REVIEW_PREFIX}{lead_id}") or {}
    return str(row.get("disposition") or "") or None


def _snapshot(svc) -> dict:
    settings = load_moltbook_settings()
    approvals = [request.redacted() for request in svc.gate.list_all()]
    pending = [item for item in approvals if item.get("decision") == "pending"]
    preparation = svc.store.get_risk(PREPARATION_KEY) or {}
    quality = _quality_snapshot(svc)
    return {
        "ok": True,
        "stage": 7,
        "mode": "owner-controlled-outbound",
        "pending_count": len(pending),
        "approvals": approvals[:50],
        "prepared_count": int(preparation.get("prepared_count") or 0),
        "outbound_enabled": settings.outbound_enabled,
        "execute_enabled": settings.execute_enabled,
        "controlled_outbound_ready": settings.controlled_outbound_ready,
        "quality_gate": quality,
        "published": any(item.get("decision") == "executed" for item in approvals),
        "note": "Approval and execution are separate owner actions. Only approved comments are executable; direct messages and autonomous writes remain disabled.",
    }


@app.get("/api/internal/moltbook-approvals")
async def get_approvals(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    return _snapshot(get_services())


@app.post("/api/internal/moltbook-approvals")
async def mutate_approvals(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    settings = load_moltbook_settings()
    body = await request.json()
    operation = str(body.get("operation") or "propose_prepared")

    if operation == "propose_prepared":
        preparation = svc.store.get_risk(PREPARATION_KEY) or {}
        items = list(preparation.get("items") or [])
        created = []
        skipped = []
        quota_reached = False
        quota_message = None
        for item in items[:8]:
            lead_id = str(item.get("lead_id") or "")
            post_id = _post_id_from_source(str(item.get("source_url") or ""))
            content = str(item.get("response_draft") or "").strip()
            if not lead_id or not post_id or not content:
                skipped.append({"lead_id": lead_id or None, "reason": "missing_post_id_or_draft"})
                continue
            try:
                req = svc.gate.propose(
                    OutboundAction.COMMENT,
                    summary=f"Prepared owner-review reply for lead {lead_id}",
                    payload={"post_id": post_id, "content": content, "parent_id": None},
                    idempotency_key=f"stage4-lead-comment:{lead_id}",
                )
            except QuotaExceededError as exc:
                quota_reached = True
                quota_message = str(exc)
                skipped.append({"lead_id": lead_id, "reason": "quota_reached"})
                break
            created.append(req.redacted())
        svc.store.append_audit(
            module="moltbook",
            action="stage4_propose_prepared",
            success=True,
            detail={"prepared": len(items), "created": len(created), "skipped": len(skipped), "quota_reached": quota_reached, "published": False},
        )
        return {**_snapshot(svc), "created": created, "skipped": skipped, "quota_reached": quota_reached, "quota_message": quota_message}

    if operation == "reject":
        request_id = str(body.get("request_id") or "").strip()
        if not request_id:
            raise HTTPException(status_code=400, detail="request_id is required")
        try:
            decided = svc.gate.decide(
                request_id,
                approved=False,
                decided_by="owner-boardroom",
                reason=str(body.get("reason") or "owner rejected"),
                expected_content_hash=body.get("expected_content_hash"),
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {**_snapshot(svc), "rejected": decided.redacted()}

    if operation == "approve":
        if not settings.outbound_enabled:
            raise HTTPException(status_code=403, detail="MOLTBOOK_OUTBOUND_ENABLED is false; owner activation is required before approval.")
        quality = _quality_snapshot(svc)
        if not quality["ready"]:
            raise HTTPException(status_code=403, detail=f"Quality gate not met: requires at least {MIN_QUALITY_REVIEWS} reviewed opportunities and {int(MIN_QUALITY_PRECISION * 100)}% positive precision.")
        request_id = str(body.get("request_id") or "").strip()
        expected_hash = str(body.get("expected_content_hash") or "").strip()
        req = svc.gate.get(request_id)
        if req is None:
            raise HTTPException(status_code=404, detail="Approval request not found")
        lead_id = _lead_id_from_summary(req.summary)
        if not lead_id or _lead_disposition(svc, lead_id) not in POSITIVE_DISPOSITIONS:
            raise HTTPException(status_code=403, detail="This opportunity must be marked Strong lead or Possible lead before approval.")
        try:
            decided = svc.gate.decide(
                request_id,
                approved=True,
                decided_by="owner-boardroom",
                reason="owner explicitly approved exact controlled comment",
                expected_content_hash=expected_hash or None,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        token = decided.approval_token
        if not token:
            raise HTTPException(status_code=500, detail="Approval token was not issued")
        return {**_snapshot(svc), "approved": decided.redacted(), "approval_token": token, "token_note": "Single-use token. Keep only in memory and execute separately."}

    if operation == "execute":
        if not settings.outbound_enabled or not settings.execute_enabled:
            raise HTTPException(status_code=403, detail="Controlled execution is not activated. Both outbound and execute gates are required.")
        request_id = str(body.get("request_id") or "").strip()
        approval_token = str(body.get("approval_token") or "").strip()
        if not request_id or not approval_token:
            raise HTTPException(status_code=400, detail="request_id and approval_token are required")
        if svc.kill_switch.engaged:
            raise HTTPException(status_code=403, detail="Kill switch engaged")
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
        return {**_snapshot(svc), "execution": result}

    if operation == "approve_and_execute":
        raise HTTPException(status_code=403, detail="Combined approve-and-execute is forbidden. Owner approval and execution must be separate actions.")

    raise HTTPException(status_code=400, detail="Unsupported operation")
