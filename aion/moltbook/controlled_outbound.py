"""Fail-closed owner-approved Moltbook comment execution.

Only exact Stage 4 COMMENT proposals may be approved and sent. No posts, follows,
DMs, subscriptions, profile changes, or autonomous writes are supported here.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import httpx

from aion.moltbook.approval import ApprovalDecision, OutboundAction
from aion.moltbook.errors import MoltbookOutboundDisabledError
from aion.moltbook.security import utc_now, utc_now_iso
from aion.moltbook.settings import load_moltbook_settings

MAX_OWNER_APPROVED_COMMENTS_PER_24H = 3


def _executed_comments_last_24h(gate) -> int:
    since = utc_now() - timedelta(hours=24)
    count = 0
    for req in gate.list_all():
        if req.action is not OutboundAction.COMMENT:
            continue
        if req.decision is not ApprovalDecision.EXECUTED or not req.executed_at:
            continue
        try:
            if __import__("datetime").datetime.fromisoformat(req.executed_at) >= since:
                count += 1
        except ValueError:
            continue
    return count


def controlled_outbound_status(gate) -> dict[str, Any]:
    settings = load_moltbook_settings()
    sent = _executed_comments_last_24h(gate)
    return {
        "outbound_enabled": settings.outbound_enabled,
        "execute_enabled": settings.execute_enabled,
        "ready": settings.controlled_outbound_ready,
        "allowed_action": "comment",
        "direct_messages_allowed": False,
        "posts_allowed": False,
        "follows_allowed": False,
        "send_quota_per_24h": MAX_OWNER_APPROVED_COMMENTS_PER_24H,
        "sent_last_24h": sent,
        "remaining_last_24h": max(0, MAX_OWNER_APPROVED_COMMENTS_PER_24H - sent),
    }


def _invalidate_after_failed_send(store, request_id: str, reason: str) -> None:
    row = store.get_approval(request_id)
    if not row:
        return
    row["decision"] = ApprovalDecision.INVALIDATED.value
    row["reason"] = reason[:500]
    row["executed_at"] = None
    store.upsert_approval(row)
    store.append_audit(
        module="moltbook",
        action="controlled_comment_send_failed",
        success=False,
        detail={"request_id": request_id, "reason": reason[:500]},
    )


async def approve_and_send_comment(
    svc,
    *,
    request_id: str,
    expected_content_hash: str,
    decided_by: str = "owner-boardroom",
) -> dict[str, Any]:
    """Approve one pending comment and make exactly one network send attempt.

    The approval token never leaves the server. The stored payload and destination
    are the only values used for the send, so edited client payloads cannot be
    substituted after approval.
    """
    settings = load_moltbook_settings()
    if not settings.controlled_outbound_ready:
        raise MoltbookOutboundDisabledError(
            "Controlled outbound is not active. Both MOLTBOOK_OUTBOUND_ENABLED=true "
            "and MOLTBOOK_PHASE2_EXECUTE=true are required."
        )
    if svc.kill_switch.engaged:
        raise MoltbookOutboundDisabledError("Kill switch engaged; outbound is blocked")
    if _executed_comments_last_24h(svc.gate) >= MAX_OWNER_APPROVED_COMMENTS_PER_24H:
        raise MoltbookOutboundDisabledError(
            f"Owner-approved send quota reached: max {MAX_OWNER_APPROVED_COMMENTS_PER_24H} comments / 24h"
        )

    pending = svc.gate.get(request_id)
    if pending is None:
        raise KeyError("Unknown approval request")
    if pending.action is not OutboundAction.COMMENT:
        raise MoltbookOutboundDisabledError("Only comment proposals can be executed in this phase")
    if pending.decision is not ApprovalDecision.PENDING:
        raise MoltbookOutboundDisabledError(f"Proposal is not pending: {pending.decision.value}")
    if pending.content_hash != expected_content_hash:
        raise MoltbookOutboundDisabledError("Content hash mismatch; proposal was not approved")

    approved = svc.gate.decide(
        request_id,
        approved=True,
        decided_by=decided_by,
        reason="explicit owner Approve & Send",
        expected_content_hash=expected_content_hash,
    )
    if not approved.approval_token:
        raise MoltbookOutboundDisabledError("Approval token was not issued")

    payload = dict(approved.payload)
    post_id = str(payload.get("post_id") or "").strip()
    content = str(payload.get("content") or "").strip()
    parent_id = payload.get("parent_id")
    if not post_id or not content:
        _invalidate_after_failed_send(svc.store, request_id, "Stored proposal is missing post_id or content")
        raise MoltbookOutboundDisabledError("Stored proposal is incomplete")

    consumed = svc.gate.consume_for_execution(
        request_id,
        approval_token=approved.approval_token,
        payload=payload,
        destination=approved.destination,
    )

    body: dict[str, Any] = {"content": content}
    if parent_id:
        body["parent_id"] = parent_id

    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.post(
                f"{settings.base_url}/posts/{post_id}/comments",
                headers={
                    "Authorization": f"Bearer {settings.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": settings.user_agent,
                },
                json=body,
            )
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        _invalidate_after_failed_send(
            svc.store,
            request_id,
            "Network outcome uncertain after single send attempt; automatic retry forbidden",
        )
        raise MoltbookOutboundDisabledError(
            "Moltbook send outcome is uncertain. AION will not retry automatically; verify the source manually."
        ) from exc

    if response.status_code < 200 or response.status_code >= 300:
        _invalidate_after_failed_send(
            svc.store,
            request_id,
            f"Moltbook comment endpoint returned HTTP {response.status_code}",
        )
        raise MoltbookOutboundDisabledError(
            f"Moltbook comment was not confirmed (HTTP {response.status_code}). Token invalidated; no automatic retry."
        )

    svc.store.append_audit(
        module="moltbook",
        action="controlled_comment_sent",
        success=True,
        detail={
            "request_id": request_id,
            "post_id": post_id,
            "status_code": response.status_code,
            "executed_at": utc_now_iso(),
        },
    )
    return {
        "published": True,
        "request": consumed.redacted(),
        "status_code": response.status_code,
        "post_id": post_id,
        "note": "One exact owner-approved comment was confirmed by Moltbook.",
    }
