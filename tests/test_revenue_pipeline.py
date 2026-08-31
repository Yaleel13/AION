from __future__ import annotations

from pathlib import Path

from aion.opportunity_store import OpportunityStore
from aion.revenue_pipeline import lead_to_opportunity, promote_leads


def _lead(**overrides):
    row = {
        "source_url": "https://www.moltbook.com/post/abc",
        "stated_problem": "Need help fixing a production website",
        "relevant_service": "Website repair",
        "fit_score": 0.85,
        "confidence_score": 0.8,
        "risks": "public identity may be an agent",
        "raw_excerpt": "Looking for help. Budget is $750 for the repair.",
    }
    row.update(overrides)
    return row


def test_lead_to_opportunity_uses_only_explicit_public_amount() -> None:
    opp = lead_to_opportunity(_lead())
    assert opp.scout == "agent_network"
    assert opp.estimated_revenue == 750
    assert opp.authorization_required == "owner_before_transaction"
    assert 0 < opp.probability <= 1


def test_lead_without_amount_does_not_invent_revenue() -> None:
    opp = lead_to_opportunity(_lead(raw_excerpt="Need help soon. Please reply."))
    assert opp.estimated_revenue == 0
    assert "Verify scope" in opp.next_action


def test_promote_leads_persists_ranked_opportunity(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    store = OpportunityStore(str(tmp_path / "opps.db"))
    promoted = promote_leads([_lead()], store)
    assert len(promoted) == 1
    ranked = store.top(limit=5)
    assert len(ranked) == 1
    assert ranked[0]["estimated_revenue"] == 750
    assert ranked[0]["authorization_required"] == "owner_before_transaction"
    store.close()
