"""Controlled commercial execution bridge for AION Revenue Engine.

Only narrowly scoped public Moltbook comment opportunities are executable today,
because AION already has a hardened exact-content, single-use approval path there.
All other commercial channels remain preparation-only until a separately reviewed
executor is added. Grant applications and federal bids are never executable here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from aion.moltbook.approval import OutboundAction, Phase2ApprovalGate
from aion.opportunity_qualification import qualify_opportunity
from aion.pursuit_packets import build_pursuit_packet


@dataclass(frozen=True, slots=True)
class CommercialExecutionPlan:
    opportunity_id: str
    executable: bool
    channel: str
    reason: str
    destination: str
    payload: dict[str, Any]
    authorization_required: str
    recommendation: str
    idempotency_key: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _moltbook_post_id(source: str) -> str:
    try:
        parsed = urlparse(source)
    except Exception:
        return ""
    host = (parsed.hostname or "").lower()
    if host not in {"moltbook.com", "www.moltbook.com"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return ""
    for marker in ("post", "posts"):
        if marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                return parts[index + 1]
    return parts[-1]


def _commercial_reply(row: dict[str, Any]) -> str:
    problem = str(row.get("customer_problem") or "this opportunity").strip()
    if len(problem) > 180:
        problem = problem[:177].rstrip() + "..."
    return (
        "Thanks for sharing this opportunity. Based on the public scope, there may be a fit "
        "with our verified technical capabilities. Before proposing terms, I would confirm "
        "the non-sensitive scope, deliverables, timeline, budget, and decision process. "
        f"Context reviewed: {problem}"
    )


def build_commercial_execution_plan(row: dict[str, Any]) -> CommercialExecutionPlan:
    qualification = qualify_opportunity(row).as_dict()
    packet = build_pursuit_packet(row)
    opportunity_id = str(row.get("opportunity_id") or "")
    approval = str(row.get("authorization_required") or "owner_before_transaction")
    source = str(row.get("source") or "")
    post_id = _moltbook_post_id(source)
    idempotency_key = f"commercial-pursuit-comment:{opportunity_id}"

    if approval in {"owner_before_application", "owner_before_bid"}:
        return CommercialExecutionPlan(
            opportunity_id=opportunity_id,
            executable=False,
            channel="preparation_only",
            reason="Grant applications and federal bids are not executable through the commercial bridge.",
            destination="",
            payload={},
            authorization_required=approval,
            recommendation=qualification["recommendation"],
            idempotency_key=idempotency_key,
        )
    if qualification["recommendation"] != "pursue_owner_review":
        return CommercialExecutionPlan(
            opportunity_id=opportunity_id,
            executable=False,
            channel="preparation_only",
            reason="Opportunity must reach pursue_owner_review before an outbound proposal can be created.",
            destination="",
            payload={},
            authorization_required=approval,
            recommendation=qualification["recommendation"],
            idempotency_key=idempotency_key,
        )
    if not post_id:
        return CommercialExecutionPlan(
            opportunity_id=opportunity_id,
            executable=False,
            channel="preparation_only",
            reason="No reviewed executable channel exists for this source yet.",
            destination="",
            payload={},
            authorization_required=approval,
            recommendation=qualification["recommendation"],
            idempotency_key=idempotency_key,
        )

    payload = {"post_id": post_id, "content": _commercial_reply(row), "parent_id": None}
    return CommercialExecutionPlan(
        opportunity_id=opportunity_id,
        executable=True,
        channel="moltbook_public_comment",
        reason="Eligible for exact-content owner approval using AION's existing hardened Moltbook comment executor.",
        destination=f"post:{post_id}",
        payload=payload,
        authorization_required=approval,
        recommendation=packet.recommendation,
        idempotency_key=idempotency_key,
    )


def propose_commercial_execution(row: dict[str, Any], gate: Phase2ApprovalGate) -> dict[str, Any]:
    plan = build_commercial_execution_plan(row)
    if not plan.executable:
        return {"created": False, "plan": plan.as_dict(), "approval": None}
    request = gate.propose(
        OutboundAction.COMMENT,
        summary=f"Commercial pursuit reply for opportunity {plan.opportunity_id}",
        payload=plan.payload,
        idempotency_key=plan.idempotency_key,
    )
    return {"created": True, "plan": plan.as_dict(), "approval": request.redacted()}


def build_execution_plans(rows: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    return [build_commercial_execution_plan(row).as_dict() for row in rows[: max(0, int(limit))]]
