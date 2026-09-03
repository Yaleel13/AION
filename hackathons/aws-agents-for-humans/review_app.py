from __future__ import annotations

from fastapi import FastAPI

from demo_fixtures import mixed_demo_opportunities
from opportunity_operator.pipeline import OpportunityLedger, process_candidates

app = FastAPI(title="AION Opportunity Operator — Strands Edition")
ledger = OpportunityLedger()


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "aion-opportunity-operator-strands",
        "mode": "human-review-only",
    }


@app.get("/demo/review")
async def demo_review() -> dict[str, object]:
    processed = process_candidates(mixed_demo_opportunities(), ledger)
    items = [
        {
            "change_state": change_state,
            "title": packet.title,
            "score": packet.score,
            "decision": packet.decision,
            "reasons": packet.reasons,
            "risks": packet.risks,
            "evidence_urls": packet.evidence_urls,
            "recommended_next_action": packet.recommended_next_action,
            "requires_human_approval": packet.requires_human_approval,
        }
        for change_state, packet in processed
    ]
    return {
        "count": len(items),
        "items": items,
        "note": "No external submission, outreach, or financial action is performed by this endpoint.",
    }
