"""AION Revenue Engine v1.

Normalizes discoveries from web, commercial, and agent-network scouts into a
shared Opportunity Ledger. Discovery never grants transaction authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any

from aion.moltbook.security import utc_now_iso


SCOUTS = frozenset({"web", "commercial", "agent_network", "owned_property", "reddit", "github"})


@dataclass(slots=True)
class Opportunity:
    opportunity_id: str
    discovered_at: str
    scout: str
    source: str
    customer_problem: str
    proposed_solution: str
    estimated_revenue: float
    estimated_cost: float
    probability: float
    capital_required: float
    time_hours: float
    major_risks: str
    ethical_considerations: str
    confidence: float
    next_action: str
    authorization_required: str
    actual_result: str = "unresolved"
    realized_value: float = 0.0

    @property
    def expected_value(self) -> float:
        gross = max(0.0, self.estimated_revenue - self.estimated_cost)
        return gross * min(1.0, max(0.0, self.probability))

    @property
    def durable_value_score(self) -> float:
        """Evidence-weighted ranking; deliberately penalizes cost/time intensity."""
        evidence = min(1.0, max(0.0, self.confidence))
        friction = 1.0 + max(0.0, self.capital_required) / 1000.0 + max(0.0, self.time_hours) / 20.0
        return (self.expected_value * evidence) / friction

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["expected_value"] = self.expected_value
        row["durable_value_score"] = self.durable_value_score
        return row


def build_opportunity(*, scout: str, source: str, customer_problem: str,
                      proposed_solution: str, estimated_revenue: float,
                      estimated_cost: float = 0.0, probability: float,
                      capital_required: float = 0.0, time_hours: float = 1.0,
                      major_risks: str = "", ethical_considerations: str = "",
                      confidence: float, next_action: str,
                      authorization_required: str = "owner_before_transaction") -> Opportunity:
    if scout not in SCOUTS:
        raise ValueError(f"Unsupported scout: {scout}")
    fingerprint = json.dumps(
        [scout, source, customer_problem, proposed_solution],
        sort_keys=True,
        separators=(",", ":"),
    )
    oid = "opp_" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:20]
    return Opportunity(
        opportunity_id=oid,
        discovered_at=utc_now_iso(),
        scout=scout,
        source=source,
        customer_problem=customer_problem,
        proposed_solution=proposed_solution,
        estimated_revenue=float(estimated_revenue),
        estimated_cost=float(estimated_cost),
        probability=float(probability),
        capital_required=float(capital_required),
        time_hours=float(time_hours),
        major_risks=major_risks,
        ethical_considerations=ethical_considerations,
        confidence=float(confidence),
        next_action=next_action,
        authorization_required=authorization_required,
    )


def rank_opportunities(items: list[Opportunity]) -> list[Opportunity]:
    return sorted(items, key=lambda item: item.durable_value_score, reverse=True)
