"""Owner-gated pursuit packet generation for qualified opportunities.

Packets turn qualification results into actionable preparation while preserving
human authority. They may draft strategy and response text, but they never submit,
send, bid, apply, register, price, or transact.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from aion.opportunity_qualification import qualify_opportunity


@dataclass(frozen=True, slots=True)
class PursuitPacket:
    opportunity_id: str
    recommendation: str
    approval_required: str
    evidence_summary: list[str]
    requirements_checklist: list[dict[str, str]]
    missing_information: list[str]
    economics: dict[str, Any]
    strategy: list[str]
    draft_material: str
    send_or_submit_enabled: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _requirements(row: dict[str, Any], qualification: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for capability in qualification.get("capability_matches") or []:
        items.append({"requirement": f"Capability match: {capability}", "status": "matched"})
    for evidence in qualification.get("eligibility_evidence") or []:
        items.append({"requirement": evidence, "status": "verified"})
    for unknown in qualification.get("unknowns") or []:
        items.append({"requirement": unknown, "status": "unknown"})
    for blocker in qualification.get("blockers") or []:
        items.append({"requirement": blocker, "status": "blocker"})
    if not items:
        items.append({"requirement": "No structured requirements extracted", "status": "verify"})
    return items


def _draft(row: dict[str, Any], qualification: dict[str, Any]) -> str:
    auth = str(row.get("authorization_required") or "owner_before_transaction")
    problem = str(row.get("customer_problem") or "Opportunity")
    source = str(row.get("source") or "")
    matches = ", ".join(qualification.get("capability_matches") or []) or "capabilities pending verification"
    unknowns = ", ".join(qualification.get("unknowns") or []) or "none identified"

    if auth == "owner_before_application":
        return (
            f"GRANT PREPARATION DRAFT — NOT SUBMITTED\n\nOpportunity: {problem}\nSource: {source}\n"
            f"Relevant capabilities: {matches}.\nOpen verification items: {unknowns}.\n\n"
            "Proposed approach: confirm applicant eligibility and official notice requirements; "
            "map only verified organizational capabilities to the stated objectives; build a factual "
            "work plan, budget basis, milestones, and evidence package; then present the completed "
            "application package to the owner for explicit approval before submission."
        )
    if auth == "owner_before_bid":
        return (
            f"BID PREPARATION DRAFT — NOT SUBMITTED\n\nOpportunity: {problem}\nSource: {source}\n"
            f"Relevant capabilities: {matches}.\nOpen verification items: {unknowns}.\n\n"
            "Proposed approach: verify solicitation scope, registration, NAICS/set-aside status, due date, "
            "representations, deliverables, and pricing basis; prepare a compliance matrix and factual "
            "capability statement; obtain owner approval before any bid, quote, certification, or submission."
        )
    return (
        f"COMMERCIAL RESPONSE DRAFT — NOT SENT\n\nOpportunity: {problem}\nSource: {source}\n"
        f"Relevant capabilities: {matches}.\nOpen verification items: {unknowns}.\n\n"
        "Draft response: Thanks for sharing the opportunity. Based on the public scope, there may be a fit "
        "with our verified technical capabilities. Before proposing terms, we would confirm the non-sensitive "
        "scope, required deliverables, timeline, budget, and decision process. Any final offer or commitment "
        "would follow owner review and approval."
    )


def build_pursuit_packet(row: dict[str, Any]) -> PursuitPacket:
    q = qualify_opportunity(row).as_dict()
    estimated_revenue = float(row.get("estimated_revenue") or 0.0)
    expected_value = float(row.get("expected_value") or 0.0)
    capital_required = float(row.get("capital_required") or 0.0)
    effort = float(q.get("effort_hours") or 0.0)
    approval = str(row.get("authorization_required") or "owner_before_transaction")

    evidence = [
        f"Source: {row.get('source') or 'unknown'}",
        f"Qualification recommendation: {q['recommendation']}",
        f"Pursuit score: {q['pursue_score']}",
        f"Capability fit: {q['capability_fit']}",
        f"Eligibility: {q['eligibility_status']}",
        f"Deadline: {q['deadline_status']}",
    ]
    if estimated_revenue > 0:
        evidence.append(f"Explicit discovered value: ${estimated_revenue:,.2f}")
    else:
        evidence.append("No verified public revenue amount found")

    strategy = [
        "Verify the original source and current availability before action.",
        "Resolve every blocker and unknown that affects eligibility, scope, economics, or deadline.",
        "Use only verified YaliTek capabilities and factual organizational claims.",
        "Prepare the required response/application/bid materials without submitting them.",
        f"Obtain explicit owner approval at gate: {approval}.",
    ]

    return PursuitPacket(
        opportunity_id=str(row.get("opportunity_id") or ""),
        recommendation=str(q["recommendation"]),
        approval_required=approval,
        evidence_summary=evidence,
        requirements_checklist=_requirements(row, q),
        missing_information=list(q.get("unknowns") or []),
        economics={
            "estimated_revenue": round(estimated_revenue, 2),
            "expected_value": round(expected_value, 2),
            "estimated_net_value": round(float(q.get("estimated_net_value") or 0.0), 2),
            "capital_required": round(capital_required, 2),
            "effort_hours": round(effort, 2),
            "probability": float(row.get("probability") or 0.0),
            "confidence": float(row.get("confidence") or 0.0),
        },
        strategy=strategy,
        draft_material=_draft(row, q),
        send_or_submit_enabled=False,
    )


def build_top_packets(rows: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for row in rows[: max(0, int(limit))]:
        packet = build_pursuit_packet(row)
        if packet.recommendation != "do_not_pursue":
            packets.append(packet.as_dict())
    return packets
