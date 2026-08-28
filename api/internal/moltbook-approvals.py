"""Moltbook approval queue and controlled owner-approved comment execution.

Stage 4 proposals remain durable and owner-reviewable. Phase 7 adds one narrow
write path: a pending COMMENT may be explicitly approved and sent once when both
controlled outbound deployment flags are enabled. No other Moltbook write action
is supported by this endpoint.
"""
from __future__ import annotations

import hmac
import os
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Request

from aion.moltbook.approval import OutboundAction
from aion.moltbook.controlled_outbound import (
    approve_and_send_comment,
    controlled_outbound_status,
)
from aion.moltbook.errors import MoltbookOutboundDisabledError
from aion.moltbook.limits import QuotaExceededError
from aion.phase2_services import get_services, reset_services_cache

app = FastAPI()
PREPARATION_KEY = "moltbook_stage3_preparation"


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


def _snapshot(svc) -> dict:
    approvals = [request.redacted() for request in svc.gate.list_all()]
    pending = [item for item in approvals if item.get("decision") == "pending"]
    preparation = svc.store.get_risk(PREPARATION_KEY) or {}
    outbound = controlled_outbound_status(svc.gate)
    return {
        "ok": True,
        "stage": 7 if outbound["ready"] else 4,
        "mode": "owner-approved-comments" if outbound["ready"] else "approval-preflight",
        "pending_count": len(pending),
        "approvals": approvals[:50],
        "prepared_count": int(preparation.get("prepared_count") or 0),
        "outbound_enabled": outbound["outbound_enabled"],
        "execute_enabled": outbound["execute_enabled"],
        "controlled_outbound": outbound,
        "published": False,
        "note": (
            "Only exact pending comment proposals can be explicitly approved and sent. "
            "No DMs, posts, follows, or autonomous writes are available."
            if outbound["ready"]
            else "Approval proposals may be created or rejected. Controlled outbound remains deployment-gated."
        ),
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
            detail={
                "prepared": len(items),
                "created": len(created),
                "skipped": len(skipped),
                "quota_reached": quota_reached,
                "quota_message": quota_message,
                "published": False,
            },
        )
        return {
            **_snapshot(svc),
            "created": created,
            "skipped": skipped,
            "quota_reached": quota_reached,
            "quota_message": quota_message,
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
                reason=str(body.get("reason") or "owner rejected during review"),
                expected_content_hash=body.get("expected_content_hash"),
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {**_snapshot(svc), "rejected": decided.redacted()}

    if operation == "approve_and_execute":
        request_id = str(body.get("request_id") or "").strip()
        expected_hash = str(body.get("expected_content_hash") or "").strip()
        if not request_id or not expected_hash:
            raise HTTPException(status_code=400, detail="request_id and expected_content_hash are required")
        try:
            result = await approve_and_send_comment(
                svc,
                request_id=request_id,
                expected_content_hash=expected_hash,
            )
        except MoltbookOutboundDisabledError as exc:
            raise HTTPException(status_code=423, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {**_snapshot(svc), **result}

    if operation in {"approve", "execute"}:
        raise HTTPException(
            status_code=403,
            detail="Separate approve-only or execute-only operations are not available. Use the explicit owner Approve & Send action so approval and exact-content execution remain bound together.",
        )

    raise HTTPException(status_code=400, detail="Unsupported operation")
