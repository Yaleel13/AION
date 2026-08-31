"""Revenue pipeline adapters.

Promotes already-qualified discoveries into the shared Opportunity Ledger without
inventing commercial facts. Revenue estimates are derived only from explicit
amounts present in source text; otherwise they remain zero pending verification.
"""

from __future__ import annotations

import re
from typing import Any

from aion.opportunity_store import OpportunityStore
from aion.revenue_engine import Opportunity, build_opportunity

_MONEY = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")


def _explicit_amount(text: str) -> float:
    amounts: list[float] = []
    for raw in _MONEY.findall(text or ""):
        try:
            amounts.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return max(amounts, default=0.0)


def lead_to_opportunity(lead: dict[str, Any]) -> Opportunity:
    """Convert a qualified lead to a safe, owner-gated opportunity."""
    source = str(lead.get("source_url") or "moltbook:unknown")
    problem = str(lead.get("stated_problem") or "Unverified buyer need")
    service = str(lead.get("relevant_service") or "Qualified commercial response")
    excerpt = str(lead.get("raw_excerpt") or "")
    risks = str(lead.get("risks") or "")
    confidence = float(lead.get("confidence_score") or 0.0)
    fit = float(lead.get("fit_score") or 0.0)
    probability = max(0.0, min(1.0, confidence * fit))
    explicit_revenue = _explicit_amount(f"{problem}\n{excerpt}")

    next_action = "Verify scope, buyer authority, budget, and payment terms before outreach"
    if explicit_revenue > 0:
        next_action = "Verify explicit budget and buyer authority, then prepare owner-reviewed outreach"

    return build_opportunity(
        scout="agent_network",
        source=source,
        customer_problem=problem,
        proposed_solution=service,
        estimated_revenue=explicit_revenue,
        estimated_cost=0.0,
        probability=probability,
        capital_required=0.0,
        time_hours=1.0,
        major_risks=risks or "Public agent identity may not represent a paying customer",
        ethical_considerations="Use public information only; no deceptive outreach or private enrichment",
        confidence=confidence,
        next_action=next_action,
        authorization_required="owner_before_transaction",
    )


def promote_leads(leads: list[dict[str, Any]], store: OpportunityStore) -> list[dict[str, Any]]:
    """Upsert leads into the Opportunity Ledger and return promoted rows."""
    promoted: list[dict[str, Any]] = []
    for lead in leads:
        opportunity = lead_to_opportunity(lead)
        store.upsert(opportunity)
        promoted.append(opportunity.to_row())
    return promoted
