"""Fail-closed owner-approved Moltbook comment execution.

This is intentionally separate from the read-only MoltbookClient. It supports
only one external write shape: a comment whose exact payload and destination
were previously approved. Both outbound and execute environment gates must be
true, and the approval token is single-use.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import httpx

from aion.moltbook.approval import ApprovalDecision, ApprovalError, OutboundAction
from aion.moltbook.errors import MoltbookError, MoltbookOutboundDisabledError
from aion.moltbook.security import content_hash, hash_token, utc_now, utc_now_iso
from aion.moltbook.settings import MoltbookSettings
from aion.moltbook.store import Phase2Store

MAX_EXECUTED_COMMENTS_PER_24H = 3


def _row_to_payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload_json")
    if isinstance(raw, str):
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _executed_comments_last_24h(store: Phase2Store) -> int:
    since = (utc_now() - timedelta(hours=24)).isoformat()
    cur = store._conn.execute(  # package-internal transaction primitive
        "SELECT COUNT(*) AS c FROM approvals WHERE action = ? AND decision = ? AND executed_at >= ?",
        (OutboundAction.COMMENT.value, ApprovalDecision.EXECUTED.value, since),
    )
    row = cur.fetchone()
    return int(row["c"] if isinstance(row, dict) or hasattr(row, "keys") else row[0])


def _claim_exact_approval(
    store: Phase2Store,
    *,
    request_id: str,
    approval_token: str,
    token_pepper: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Atomically claim a single approved request before the network write."""
    conn = store._conn  # same package; required for row lock / BEGIN IMMEDIATE
    try:
        conn.begin_immediate()
        sql = "SELECT * FROM approvals WHERE request_id = ?"
        if getattr(conn, "backend", "sqlite") == "postgres":
            sql += " FOR UPDATE"
        cur = conn.execute(sql, (request_id,))
        row_obj = cur.fetchone()
        if row_obj is None:
            raise ApprovalError("Unknown approval request")
        row = dict(row_obj)
        if row.get("decision") != ApprovalDecision.APPROVED.value:
            raise ApprovalError(f"Not approved: {row.get('decision')}")
        if row.get("token_consumed_at"):
            raise ApprovalError("Approval token already consumed")
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                expires = datetime.fromisoformat(str(expires_at))
            except ValueError as exc:
                raise ApprovalError("Approval has an invalid expiry timestamp") from exc
            if utc_now() > expires:
                raise ApprovalError("Approval expired")
        payload = _row_to_payload(row)
        destination = f"post:{payload.get('post_id')}"
        expected_hash = content_hash(
            {"action": row.get("action"), "destination": destination, "payload": payload}
        )
        if destination != row.get("destination") or expected_hash != row.get("content_hash"):
            raise ApprovalError("Approval invalidated: content or destination changed")
        provided_hash = hash_token(approval_token, pepper=token_pepper)
        if not row.get("approval_token_hash") or provided_hash != row.get("approval_token_hash"):
            raise ApprovalError("Invalid approval token")
        claimed_at = utc_now_iso()
        conn.execute(
            "UPDATE approvals SET token_consumed_at = ? WHERE request_id = ? AND token_consumed_at IS NULL",
            (claimed_at, request_id),
        )
        conn.commit()
        row["token_consumed_at"] = claimed_at
        return row, payload
    except Exception:
        conn.rollback()
        raise


def _finish(store: Phase2Store, request_id: str, *, success: bool, reason: str | None = None) -> None:
    now = utc_now_iso()
    if success:
        store._conn.execute(
            "UPDATE approvals SET decision = ?, executed_at = ?, reason = ? WHERE request_id = ?",
            (ApprovalDecision.EXECUTED.value, now, reason, request_id),
        )
    else:
        store._conn.execute(
            "UPDATE approvals SET decision = ?, reason = ? WHERE request_id = ?",
            (ApprovalDecision.INVALIDATED.value, reason or "external execution failed after token claim", request_id),
        )
    store._conn.commit()


async def execute_approved_comment(
    store: Phase2Store,
    settings: MoltbookSettings,
    *,
    request_id: str,
    approval_token: str,
    token_pepper: str,
) -> dict[str, Any]:
    if not settings.outbound_enabled:
        raise MoltbookOutboundDisabledError("MOLTBOOK_OUTBOUND_ENABLED is false")
    if not settings.execute_enabled:
        raise MoltbookOutboundDisabledError("MOLTBOOK_EXECUTE_ENABLED is false")
    if not settings.configured_for_live:
        raise MoltbookOutboundDisabledError("Live Moltbook credentials are not configured")
    if _executed_comments_last_24h(store) >= MAX_EXECUTED_COMMENTS_PER_24H:
        raise MoltbookOutboundDisabledError(
            f"Executed comment quota reached: max {MAX_EXECUTED_COMMENTS_PER_24H} / 24h"
        )

    row, payload = _claim_exact_approval(
        store,
        request_id=request_id,
        approval_token=approval_token,
        token_pepper=token_pepper,
    )
    if row.get("action") != OutboundAction.COMMENT.value:
        _finish(store, request_id, success=False, reason="Only comments are executable in Phase 7")
        raise MoltbookOutboundDisabledError("Only comments are executable in Phase 7")

    post_id = str(payload.get("post_id") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not post_id or not content:
        _finish(store, request_id, success=False, reason="Missing approved post_id or content")
        raise ApprovalError("Missing approved post_id or content")

    body: dict[str, Any] = {"content": content}
    if payload.get("parent_id"):
        body["parent_id"] = payload["parent_id"]

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
        if response.status_code >= 400:
            reason = f"Moltbook comment failed with HTTP {response.status_code}"
            _finish(store, request_id, success=False, reason=reason)
            store.append_audit(
                module="moltbook",
                action="controlled_comment_execute",
                success=False,
                detail={"request_id": request_id, "status_code": response.status_code},
            )
            raise MoltbookError(reason)
        _finish(store, request_id, success=True, reason="owner-approved controlled comment executed")
        store.append_audit(
            module="moltbook",
            action="controlled_comment_execute",
            success=True,
            detail={"request_id": request_id, "status_code": response.status_code},
        )
        result = response.json() if response.content else {}
        return {
            "ok": True,
            "request_id": request_id,
            "status_code": response.status_code,
            "result": result if isinstance(result, dict) else {"data": result},
        }
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        _finish(store, request_id, success=False, reason="Moltbook transport failure after token claim")
        store.append_audit(
            module="moltbook",
            action="controlled_comment_execute",
            success=False,
            detail={"request_id": request_id, "error_type": type(exc).__name__},
        )
        raise MoltbookError("Moltbook transport failure; approval invalidated and will not auto-retry") from exc
