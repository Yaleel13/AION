from __future__ import annotations

from datetime import datetime, timezone

from opportunity_operator.models import Evidence, Opportunity


def mixed_demo_opportunities() -> list[Opportunity]:
    future = datetime(2026, 9, 14, 21, 0, tzinfo=timezone.utc)
    past = datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc)

    return [
        Opportunity(
            title="Verified AI agent hackathon",
            opportunity_type="hackathon",
            summary="Officially announced agent hackathon with cash prizes and no purchase requirement.",
            payout_value_usd=10000,
            effort_hours=16,
            deadline=future,
            eligibility_score=9,
            credibility_score=10,
            fit_score=10,
            urgency_score=9,
            evidence=[
                Evidence(
                    source_url="https://example.org/official-hackathon",
                    source_name="Official sponsor page",
                    official=True,
                )
            ],
        ),
        Opportunity(
            title="Paid AI automation contract",
            opportunity_type="freelance_contract",
            summary="Buyer requests production n8n and agent automation work.",
            payout_value_usd=7500,
            effort_hours=50,
            eligibility_score=8,
            credibility_score=8,
            fit_score=10,
            urgency_score=8,
            evidence=[
                Evidence(
                    source_url="https://example.org/marketplace-contract",
                    source_name="Marketplace listing",
                    official=True,
                )
            ],
        ),
        Opportunity(
            title="Stale open-source bounty",
            opportunity_type="open_source_paid_issue",
            summary="Old bounty with no current activity.",
            payout_value_usd=1000,
            effort_hours=30,
            deadline=past,
            eligibility_score=8,
            credibility_score=5,
            fit_score=7,
            urgency_score=1,
            is_expired=True,
            evidence=[
                Evidence(
                    source_url="https://example.org/old-bounty",
                    source_name="Official issue",
                    official=True,
                )
            ],
        ),
        Opportunity(
            title="Reddit rumor about a grant",
            opportunity_type="grant",
            summary="Community post claims a new AI grant exists but no sponsor page is available.",
            payout_value_usd=25000,
            effort_hours=8,
            eligibility_score=7,
            credibility_score=2,
            fit_score=9,
            urgency_score=6,
            evidence=[
                Evidence(
                    source_url="https://www.reddit.com/r/example/comments/grant-rumor",
                    source_name="Reddit discovery post",
                    official=False,
                )
            ],
        ),
        Opportunity(
            title="Wallet-connect promo",
            opportunity_type="web3_paid_work",
            summary="Promotional offer requires connecting a wallet before work can be reviewed.",
            payout_value_usd=3000,
            effort_hours=4,
            eligibility_score=8,
            credibility_score=4,
            fit_score=8,
            urgency_score=7,
            requires_wallet_connection_to_qualify=True,
            evidence=[
                Evidence(
                    source_url="https://example.org/wallet-promo",
                    source_name="Official campaign page",
                    official=True,
                )
            ],
        ),
        Opportunity(
            title="Token speculation challenge",
            opportunity_type="web3_paid_work",
            summary="Contest rewards predictions about short-term token price movement.",
            payout_value_usd=5000,
            effort_hours=6,
            eligibility_score=9,
            credibility_score=7,
            fit_score=4,
            urgency_score=7,
            is_speculative_trading=True,
            evidence=[
                Evidence(
                    source_url="https://example.org/token-challenge",
                    source_name="Official challenge page",
                    official=True,
                )
            ],
        ),
    ]
