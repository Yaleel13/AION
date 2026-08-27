"""Phase 2 approval gate: single-use tokens, expiry, content hashing, quotas.

Phase 1 ``OutboundApprovalGate`` remains available for backward-compatible tests
and always refuses execution. Phase 2 uses ``Phase2ApprovalGate``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aion.moltbook.errors import MoltbookError, MoltbookOutboundDisabledError
from aion.moltbook.limits import QuotaExceededError, QuotaGuard
from aion.moltbook.redact import redact_value
from aion.moltbook.security import (
    KillSwitch,
    content_hash,
    detect_prompt_injection,
    hash_token,
    new_token,
    utc_now,
    utc_now_iso,
)
from aion.moltbook.store import Phase2Store


class OutboundAction(str, Enum):
    """Outbound actions that must never run without explicit owner approval."""

    CREATE_POST = "create_post"
    COMMENT = "comment"
    FOLLOW = "follow"
    SUBSCRIBE = "subscribe"
    VOTE = "vote"
    REGISTER_AGENT = "register_agent"
    UPDATE_PROFILE = "update_profile"
    DELETE_CONTENT = "delete_content"
    DIRECT_MESSAGE = "direct_message"


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    INVALIDATED = "invalidated"


class ApprovalError(MoltbookError):
    """Raised for invalid approval lifecycle transitions."""


@dataclass(slots=True)
class ApprovalRequest:
    """A proposed outbound action awaiting human decision."""

    action: OutboundAction
    summary: str
    payload: dict[str, Any]
    destination: str = ""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    decision: ApprovalDecision = ApprovalDecision.PENDING
    content_hash: str = ""
    idempotency_key: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    expires_at: str = ""
    decided_at: str | None = None
    decided_by: str | None = None
    reason: str | None = None
    injection_flags: list[str] = field(default_factory=list)
    # Raw token is only returned once at approve-time; never persisted.
    approval_token: str | None = None
    token_consumed_at: str | None = None
    executed_at: str | None = None

    def redacted(self) -> dict[str, Any]:
        return redact_value(
            {
                "request_id": self.request_id,
                "action": self.action.value,
                "summary": self.summary,
                "destination": self.destination,
                "payload": self.payload,
                "content_hash": self.content_hash,
                "idempotency_key": self.idempotency_key,
                "decision": self.decision.value,
                "created_at": self.created_at,
                "expires_at": self.expires_at,
                "decided_at": self.decided_at,
                "decided_by": self.decided_by,
                "reason": self.reason,
                "injection_flags": self.injection_flags,
                "approval_token_present": bool(self.approval_token),
                "token_consumed_at": self.token_consumed_at,
                "executed_at": self.executed_at,
            }
        )


def _destination_for(action: OutboundAction, payload: dict[str, Any]) -> str:
    if action is OutboundAction.CREATE_POST:
        return f"submolt:{payload.get('submolt') or payload.get('submolt_name')}"
    if action is OutboundAction.COMMENT:
        return f"post:{payload.get('post_id')}"
    if action is OutboundAction.FOLLOW:
        return f"agent:{payload.get('agent_name')}"
    if action is OutboundAction.UPDATE_PROFILE:
        return "profile:self"
    if action is OutboundAction.DIRECT_MESSAGE:
        return f"dm:{payload.get('recipient')}"
    if action is OutboundAction.SUBSCRIBE:
        return f"submolt:{payload.get('submolt')}"
    return action.value


def _payload_text_blob(payload: dict[str, Any]) -> str:
    parts = []
    for key in ("title", "content", "body", "summary", "message", "description"):
        val = payload.get(key)
        if isinstance(val, str):
            parts.append(val)
    return "\n".join(parts)


class OutboundApprovalGate:
    """Phase 1 in-memory gate — proposals only; execution always denied."""

    def __init__(self, *, phase: str = "phase1-readonly"):
        self.phase = phase
        self._requests: dict[str, ApprovalRequest] = {}

    def propose(
        self,
        action: OutboundAction,
        *,
        summary: str,
        payload: dict[str, Any],
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            action=action,
            summary=summary,
            payload=payload,
            destination=_destination_for(action, payload),
            content_hash=content_hash(payload),
        )
        self._requests[request.request_id] = request
        return request

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return [
            req
            for req in self._requests.values()
            if req.decision is ApprovalDecision.PENDING
        ]

    def decide(
        self,
        request_id: str,
        *,
        approved: bool,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Unknown approval request: {request_id}")
        request.decision = (
            ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED
        )
        request.decided_at = utc_now_iso()
        request.decided_by = decided_by
        request.reason = reason
        return request

    def assert_executable(self, request: ApprovalRequest) -> None:
        raise MoltbookOutboundDisabledError(
            f"Outbound action {request.action.value} is disabled in {self.phase}. "
            "Use Phase2ApprovalGate with a single-use owner token for controlled execution."
        )


class Phase2ApprovalGate:
    """Persistent approval queue with single-use tokens and expiry."""

    def __init__(
        self,
        store: Phase2Store,
        *,
        kill_switch: KillSwitch | None = None,
        token_pepper: str | None = None,
        approval_ttl_hours: int = 24,
        quotas: QuotaGuard | None = None,
        allow_direct_messages: bool = False,
    ):
        self.store = store
        self.kill_switch = kill_switch or KillSwitch.from_env()
        self.token_pepper = token_pepper or os.getenv(
            "AION_APPROVAL_TOKEN_PEPPER", "dev-only-change-me"
        )
        self.approval_ttl_hours = approval_ttl_hours
        self.quotas = quotas or QuotaGuard(store)
        self.allow_direct_messages = allow_direct_messages

    def _row_to_request(self, row: dict[str, Any]) -> ApprovalRequest:
        return ApprovalRequest(
            request_id=row["request_id"],
            action=OutboundAction(row["action"]),
            summary=row["summary"],
            destination=row["destination"],
            payload=json.loads(row["payload_json"]),
            content_hash=row["content_hash"],
            idempotency_key=row["idempotency_key"],
            decision=ApprovalDecision(row["decision"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            decided_at=row["decided_at"],
            decided_by=row["decided_by"],
            reason=row["reason"],
            injection_flags=json.loads(row.get("injection_flags_json") or "[]"),
            token_consumed_at=row["token_consumed_at"],
            executed_at=row["executed_at"],
        )

    def _persist(self, req: ApprovalRequest, *, token_hash: str | None = None) -> None:
        existing = self.store.get_approval(req.request_id)
        self.store.upsert_approval(
            {
                "request_id": req.request_id,
                "action": req.action.value,
                "summary": req.summary,
                "destination": req.destination,
                "payload_json": json.dumps(req.payload, default=str),
                "content_hash": req.content_hash,
                "idempotency_key": req.idempotency_key,
                "decision": req.decision.value,
                "created_at": req.created_at,
                "expires_at": req.expires_at,
                "decided_at": req.decided_at,
                "decided_by": req.decided_by,
                "reason": req.reason,
                "approval_token_hash": token_hash
                if token_hash is not None
                else (existing or {}).get("approval_token_hash"),
                "token_consumed_at": req.token_consumed_at,
                "executed_at": req.executed_at,
                "injection_flags_json": json.dumps(req.injection_flags),
            }
        )

    def propose(
        self,
        action: OutboundAction,
        *,
        summary: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        ttl_hours: int | None = None,
    ) -> ApprovalRequest:
        if self.kill_switch.engaged:
            raise MoltbookOutboundDisabledError(
                f"Kill switch engaged: {self.kill_switch.reason}"
            )
        if action is OutboundAction.DIRECT_MESSAGE and not self.allow_direct_messages:
            raise QuotaExceededError(
                "Unsolicited direct messages are forbidden in Phase 2"
            )

        self.quotas.assert_can_propose(action.value)

        if idempotency_key:
            existing = self.store.get_approval_by_idempotency(idempotency_key)
            if existing:
                return self._row_to_request(existing)

        destination = _destination_for(action, payload)
        hashed = content_hash({"action": action.value, "destination": destination, "payload": payload})
        flags = detect_prompt_injection(_payload_text_blob(payload))
        expires = utc_now() + timedelta(hours=ttl_hours or self.approval_ttl_hours)
        req = ApprovalRequest(
            action=action,
            summary=summary,
            payload=payload,
            destination=destination,
            content_hash=hashed,
            idempotency_key=idempotency_key or str(uuid4()),
            expires_at=expires.isoformat(),
            injection_flags=flags,
        )
        self._persist(req)
        self.store.append_audit(
            module="approval",
            action="propose",
            success=True,
            detail=req.redacted(),
        )
        return req

    def get(self, request_id: str) -> ApprovalRequest | None:
        row = self.store.get_approval(request_id)
        if not row:
            return None
        req = self._row_to_request(row)
        self._expire_if_needed(req, row)
        return req

    def list_pending(self) -> list[ApprovalRequest]:
        pending = []
        for row in self.store.list_approvals(decision=ApprovalDecision.PENDING.value):
            req = self._row_to_request(row)
            if self._expire_if_needed(req, row):
                continue
            pending.append(req)
        return pending

    def list_all(self) -> list[ApprovalRequest]:
        return [self._row_to_request(row) for row in self.store.list_approvals()]

    def _expire_if_needed(self, req: ApprovalRequest, row: dict[str, Any]) -> bool:
        if req.decision is not ApprovalDecision.PENDING and req.decision is not ApprovalDecision.APPROVED:
            return False
        if req.expires_at and utc_now() > datetime.fromisoformat(req.expires_at):
            req.decision = ApprovalDecision.EXPIRED
            req.reason = (req.reason or "") + " | expired"
            self._persist(req, token_hash=row.get("approval_token_hash"))
            self.store.append_audit(
                module="approval",
                action="expire",
                success=True,
                detail={"request_id": req.request_id},
            )
            return True
        return False

    def decide(
        self,
        request_id: str,
        *,
        approved: bool,
        decided_by: str,
        reason: str | None = None,
        expected_content_hash: str | None = None,
    ) -> ApprovalRequest:
        row = self.store.get_approval(request_id)
        if row is None:
            raise KeyError(f"Unknown approval request: {request_id}")
        req = self._row_to_request(row)
        if self._expire_if_needed(req, row):
            raise ApprovalError("Approval request has expired")
        if req.decision is not ApprovalDecision.PENDING:
            raise ApprovalError(f"Request already decided: {req.decision.value}")

        if expected_content_hash and expected_content_hash != req.content_hash:
            req.decision = ApprovalDecision.INVALIDATED
            req.decided_at = utc_now_iso()
            req.decided_by = decided_by
            req.reason = "content hash mismatch at decision time"
            self._persist(req)
            raise ApprovalError("Content hash mismatch — approval invalidated")

        req.decided_at = utc_now_iso()
        req.decided_by = decided_by
        req.reason = reason
        token_hash = None
        if approved:
            if self.kill_switch.engaged:
                raise MoltbookOutboundDisabledError("Kill switch engaged; cannot approve")
            raw = new_token()
            token_hash = hash_token(raw, pepper=self.token_pepper)
            req.decision = ApprovalDecision.APPROVED
            req.approval_token = raw  # returned once to owner
        else:
            req.decision = ApprovalDecision.REJECTED

        self._persist(req, token_hash=token_hash)
        self.store.append_audit(
            module="approval",
            action="decide",
            success=True,
            detail={
                "request_id": req.request_id,
                "decision": req.decision.value,
                "decided_by": decided_by,
            },
        )
        return req

    def consume_for_execution(
        self,
        request_id: str,
        *,
        approval_token: str,
        payload: dict[str, Any],
        destination: str,
    ) -> ApprovalRequest:
        """Validate single-use token + exact content/destination binding.

        Does not perform the network side-effect. Callers must still respect
        kill switch and Phase 2 execute flags. Marks token consumed / executed.
        """
        if self.kill_switch.engaged:
            raise MoltbookOutboundDisabledError(
                f"Kill switch engaged: {self.kill_switch.reason}"
            )
        row = self.store.get_approval(request_id)
        if row is None:
            raise ApprovalError("Unknown approval request")
        req = self._row_to_request(row)
        if self._expire_if_needed(req, row):
            raise ApprovalError("Approval expired")
        if req.decision is not ApprovalDecision.APPROVED:
            raise ApprovalError(f"Not approved: {req.decision.value}")
        if row.get("token_consumed_at"):
            raise ApprovalError("Approval token already consumed")

        expected_hash = content_hash(
            {"action": req.action.value, "destination": destination, "payload": payload}
        )
        if destination != req.destination or expected_hash != req.content_hash:
            req.decision = ApprovalDecision.INVALIDATED
            req.reason = "content or destination changed after approval"
            self._persist(req, token_hash=row.get("approval_token_hash"))
            raise ApprovalError(
                "Approval invalidated: content or destination does not match approval"
            )

        provided_hash = hash_token(approval_token, pepper=self.token_pepper)
        if not row.get("approval_token_hash") or provided_hash != row["approval_token_hash"]:
            raise ApprovalError("Invalid approval token")

        req.token_consumed_at = utc_now_iso()
        req.executed_at = utc_now_iso()
        req.decision = ApprovalDecision.EXECUTED
        self._persist(req, token_hash=row.get("approval_token_hash"))
        self.store.append_audit(
            module="approval",
            action="consume_token",
            success=True,
            detail={"request_id": req.request_id, "action": req.action.value},
        )
        return req
