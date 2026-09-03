from __future__ import annotations

from types import SimpleNamespace

from aion.opportunity_store import OpportunityStore
from aion.revenue.lead_checkout import prepare_lead_checkout
from aion.revenue.product_catalog import PRODUCTS


def test_prepare_lead_checkout_allows_reddit_source_without_post_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    store = OpportunityStore(str(tmp_path / "ops.db"))
    product = next(p for p in PRODUCTS if p.product_key == "quick-tech-diagnostic")
    result = prepare_lead_checkout(
        lead={
            "lead_id": "lead-reddit-1",
            "source_url": "https://www.reddit.com/r/forhire/comments/abc/hiring/",
            "source_post_id": "",
        },
        product=product,
        store=store,
    )
    # Stripe client is not live in unit tests; attribution must still be accepted.
    assert result["reason"] != "missing_attribution_ids"
    store.close()


def test_emergency_diagnostic_is_fixed_price() -> None:
    product = next(p for p in PRODUCTS if p.product_key == "emergency-diagnostic")
    result = prepare_lead_checkout(
        lead={"lead_id": "x", "source_url": "https://www.moltbook.com/post/p1", "source_post_id": "p1"},
        product=product,
        store=SimpleNamespace(),
    )
    assert result.get("reason") != "product_not_fixed_price"
