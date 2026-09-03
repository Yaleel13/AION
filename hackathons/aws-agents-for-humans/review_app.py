from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from demo_fixtures import mixed_demo_opportunities
from opportunity_operator.observability import configure_logging, emit_event
from opportunity_operator.persistent_ledger import JsonOpportunityLedger
from opportunity_operator.pipeline import process_candidates

configure_logging()
app = FastAPI(title="AION Opportunity Operator — Strands Edition")
ledger_path = Path(os.getenv("OPPORTUNITY_LEDGER_PATH", ".data/opportunity-ledger.json"))
ledger = JsonOpportunityLedger(ledger_path)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "aion-opportunity-operator-strands",
        "mode": "human-review-only",
        "ledger": str(ledger_path),
    }


@app.get("/demo/review")
async def demo_review() -> dict[str, object]:
    processed = process_candidates(mixed_demo_opportunities(), ledger)
    items = []
    for change_state, packet in processed:
        emit_event(
            "candidate_reviewed",
            change_state=change_state,
            title=packet.title,
            score=packet.score,
            decision=packet.decision,
        )
        items.append(
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
        )
    return {
        "count": len(items),
        "items": items,
        "note": "No external submission, outreach, or financial action is performed by this endpoint.",
    }
