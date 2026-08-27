"""Proposed approval system for future Moltbook outbound actions.

Phase 1 does not execute outbound actions. This module defines the approval
contract so Phase 2 can plug in without rewriting call sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aion.moltbook.errors import MoltbookOutboundDisabledError
from aion.moltbook.redact import redact_value


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


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(slots=True)
class ApprovalRequest:
    """A proposed outbound action awaiting human decision."""

    action: OutboundAction
    summary: str
    payload: dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid4()))
    decision: ApprovalDecision = ApprovalDecision.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    decided_at: str | None = None
    decided_by: str | None = None
    reason: str | None = None

    def redacted(self) -> dict[str, Any]:
        return redact_value(
            {
                "request_id": self.request_id,
                "action": self.action.value,
                "summary": self.summary,
                "payload": self.payload,
                "decision": self.decision.value,
                "created_at": self.created_at,
                "decided_at": self.decided_at,
                "decided_by": self.decided_by,
                "reason": self.reason,
            }
        )


class OutboundApprovalGate:
    """In-memory proposal queue for future outbound Moltbook actions.

    Phase 1 behavior:
    - Proposals may be recorded for review.
    - Execution always raises ``MoltbookOutboundDisabledError``.
    - Even an "approved" decision cannot execute until Phase 2 enables outbound.
    """

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
        request = ApprovalRequest(action=action, summary=summary, payload=payload)
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
        request.decided_at = datetime.now(timezone.utc).isoformat()
        request.decided_by = decided_by
        request.reason = reason
        return request

    def assert_executable(self, request: ApprovalRequest) -> None:
        """Phase 1 hard stop: outbound never executes."""
        raise MoltbookOutboundDisabledError(
            f"Outbound action {request.action.value} is disabled in {self.phase}. "
            "Record an approval proposal for review, but do not execute until "
            "Phase 2 outbound enablement is explicitly accepted by the owner."
        )
