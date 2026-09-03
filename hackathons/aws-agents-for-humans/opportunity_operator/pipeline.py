from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from .models import DecisionPacket, Opportunity
from .scoring import evaluate_opportunity


def opportunity_fingerprint(opportunity: Opportunity) -> str:
    payload = {
        "title": opportunity.title.strip().lower(),
        "type": opportunity.opportunity_type,
        "evidence": sorted(str(item.source_url) for item in opportunity.evidence),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def material_signature(opportunity: Opportunity) -> str:
    payload = {
        "payout_value_usd": opportunity.payout_value_usd,
        "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
        "eligibility_score": opportunity.eligibility_score,
        "credibility_score": opportunity.credibility_score,
        "fit_score": opportunity.fit_score,
        "urgency_score": opportunity.urgency_score,
        "requires_upfront_payment": opportunity.requires_upfront_payment,
        "requires_wallet_connection_to_qualify": opportunity.requires_wallet_connection_to_qualify,
        "is_speculative_trading": opportunity.is_speculative_trading,
        "is_gambling": opportunity.is_gambling,
        "is_expired": opportunity.is_expired,
        "unverifiable_payment_claim": opportunity.unverifiable_payment_claim,
        "official_sources": sorted(
            str(item.source_url) for item in opportunity.evidence if item.official
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def has_official_evidence(opportunity: Opportunity) -> bool:
    return any(item.official for item in opportunity.evidence)


def verification_reasons(opportunity: Opportunity) -> list[str]:
    reasons: list[str] = []
    if not opportunity.evidence:
        reasons.append("no evidence source supplied")
    elif not has_official_evidence(opportunity):
        reasons.append("no official/high-authority source independently verifies the opportunity")
    return reasons


@dataclass
class LedgerEntry:
    fingerprint: str
    material_signature: str
    last_seen_at: datetime
    decision: str


@dataclass
class OpportunityLedger:
    entries: dict[str, LedgerEntry] = field(default_factory=dict)

    def classify(self, opportunity: Opportunity) -> str:
        fingerprint = opportunity_fingerprint(opportunity)
        signature = material_signature(opportunity)
        previous = self.entries.get(fingerprint)
        if previous is None:
            return "new"
        if previous.material_signature != signature:
            return "materially_changed"
        return "unchanged"

    def record(self, opportunity: Opportunity, packet: DecisionPacket) -> None:
        fingerprint = opportunity_fingerprint(opportunity)
        self.entries[fingerprint] = LedgerEntry(
            fingerprint=fingerprint,
            material_signature=material_signature(opportunity),
            last_seen_at=datetime.now(timezone.utc),
            decision=packet.decision,
        )


def process_candidates(
    candidates: Iterable[Opportunity],
    ledger: OpportunityLedger,
) -> list[tuple[str, DecisionPacket]]:
    """Return only new/materially changed candidates worth recording.

    Social-only or otherwise unverified opportunities are rejected before scoring.
    Unchanged items are intentionally silent so a background run does not spam the
    human reviewer.
    """
    results: list[tuple[str, DecisionPacket]] = []
    seen_batch: set[str] = set()

    for opportunity in candidates:
        fingerprint = opportunity_fingerprint(opportunity)
        if fingerprint in seen_batch:
            continue
        seen_batch.add(fingerprint)

        change_state = ledger.classify(opportunity)
        if change_state == "unchanged":
            continue

        verification = verification_reasons(opportunity)
        if verification:
            packet = DecisionPacket(
                title=opportunity.title,
                score=0.0,
                decision="reject",
                reasons=verification,
                risks=["discovery lead is not independently verified"],
                evidence_urls=[str(item.source_url) for item in opportunity.evidence],
                recommended_next_action="Find and verify an official source before reconsidering.",
                requires_human_approval=True,
            )
        else:
            packet = evaluate_opportunity(opportunity)

        ledger.record(opportunity, packet)
        results.append((change_state, packet))

    return results
