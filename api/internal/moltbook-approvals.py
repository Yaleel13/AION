"""Stage 4 approval preflight for Moltbook outbound proposals.

This endpoint may create persistent approval requests from Stage 3 prepared
opportunities and may reject pending requests. It deliberately cannot approve,
execute, contact, or publish anything. Live network writes require a separate
explicit activation review.
"""
from __future__ import annotations

import hmac
import os
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Request

from aion.moltbook.approval import OutboundAction
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
    return {
        "ok": True,
        "stage": 4,
        "mode": "approval-preflight",
        "pending_count": len(pending),
        "approvals": approvals[:50],
        "prepared_count": int(preparation.get("prepared_count") or 0),
        "outbound_enabled": False,
        "execute_enabled": False,
        "published": False,
        "note": "Approval proposals may be created or rejected. Approval-and-execution remains disabled in this build.",
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
        for item in items[:12]:
            lead_id = str(item.get("lead_id") or "")
            post_id = _post_id_from_source(str(item.get("source_url") or ""))
            content = str(item.get("response_draft") or "").strip()
            if not lead_id or not post_id or not content:
                skipped.append({"lead_id": lead_id or None, "reason": "missing_post_id_or_draft"})
                continue
            req = svc.gate.propose(
                OutboundAction.COMMENT,
                summary=f"Prepared owner-review reply for lead {lead_id}",
                payload={"post_id": post_id, "content": content, "parent_id": None},
                idempotency_key=f"stage4-lead-comment:{lead_id}",
            )
            created.append(req.redacted())
        svc.store.append_audit(
            module="moltbook",
            action="stage4_propose_prepared",
            success=True,
            detail={"prepared": len(items), "created": len(created), "skipped": len(skipped), "published": False},
        )
        return {**_snapshot(svc), "created": created, "skipped": skipped}

    if operation == "reject":
        request_id = str(body.get("request_id") or "").strip()
        if not request_id:
            raise HTTPException(status_code=400, detail="request_id is required")
        try:
            decided = svc.gate.decide(
                request_id,
                approved=False,
                decided_by="owner-boardroom",
                reason=str(body.get("reason") or "owner rejected during Stage 4 preflight"),
                expected_content_hash=body.get("expected_content_hash"),
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {**_snapshot(svc), "rejected": decided.redacted()}

    if operation in {"approve", "execute", "approve_and_execute"}:
        raise HTTPException(
            status_code=403,
            detail="Approval-and-execution is intentionally disabled in Stage 4 preflight. A separate explicit live-write activation review is required.",
        )

    raise HTTPException(status_code=400, detail="Unsupported operation")
