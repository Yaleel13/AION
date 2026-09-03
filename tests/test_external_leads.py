from __future__ import annotations

from pathlib import Path

from aion.moltbook.store import Phase2Store
from aion.revenue.external_leads import opportunity_to_lead, promote_external_opportunities_to_leads


def test_opportunity_to_lead_promotes_reddit_buyer_intent() -> None:
    lead = opportunity_to_lead(
        {
            "scout": "reddit",
            "source": "https://www.reddit.com/r/forhire/comments/abc/hiring/",
            "customer_problem": "Looking to hire a developer for WordPress website repair",
            "proposed_solution": "Match to an existing YaliTek service",
            "confidence": 0.84,
            "authorization_required": "owner_before_transaction",
        }
    )
    assert lead is not None
    assert "intent_signal=explicit" in lead["risks"]
    assert "does not auto-comment" in lead["risks"]
    assert lead["source_url"].startswith("https://www.reddit.com/")


def test_opportunity_to_lead_skips_federal_grants() -> None:
    assert (
        opportunity_to_lead(
            {
                "scout": "web",
                "source": "https://www.grants.gov/search-results-detail/123",
                "customer_problem": "Grant opportunity: AI research",
                "proposed_solution": "Verify eligibility",
                "confidence": 0.9,
                "authorization_required": "owner_before_application",
            }
        )
        is None
    )


def test_opportunity_to_lead_skips_low_confidence() -> None:
    assert (
        opportunity_to_lead(
            {
                "scout": "github",
                "source": "https://github.com/acme/app/issues/1",
                "customer_problem": "Need help with Next.js hosting deploy",
                "proposed_solution": "Match to YaliTek",
                "confidence": 0.4,
                "authorization_required": "owner_before_transaction",
            }
        )
        is None
    )


def test_promote_external_opportunities_persists_lead(tmp_path: Path) -> None:
    store = Phase2Store(str(tmp_path / "phase2.db"))
    promoted = promote_external_opportunities_to_leads(
        [
            {
                "scout": "commercial",
                "source": "https://news.ycombinator.com/item?id=999",
                "customer_problem": "Seeking freelancer for Next.js and Stripe integration. Budget $1200.",
                "proposed_solution": "Match to an existing YaliTek service",
                "confidence": 0.9,
                "authorization_required": "owner_before_transaction",
            }
        ],
        store,
    )
    assert len(promoted) == 1
    stored = store.list_leads()
    assert stored[0]["source_url"] == "https://news.ycombinator.com/item?id=999"
    store.close()
