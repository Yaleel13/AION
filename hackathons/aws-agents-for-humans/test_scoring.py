from datetime import datetime, timezone

from opportunity_operator.models import Evidence, Opportunity
from opportunity_operator.scoring import evaluate_opportunity


def official_evidence(url: str = "https://example.com/opportunity") -> Evidence:
    return Evidence(
        source_url=url,
        source_name="Official sponsor",
        official=True,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_high_value_verified_opportunity_is_reviewed() -> None:
    result = evaluate_opportunity(
        Opportunity(
            title="Verified AI hackathon",
            opportunity_type="hackathon",
            summary="A legitimate technical competition.",
            payout_value_usd=10000,
            effort_hours=12,
            eligibility_score=9,
            credibility_score=10,
            fit_score=10,
            urgency_score=8,
            evidence=[official_evidence()],
        )
    )
    assert result.decision == "review"
    assert result.score >= 6.0
    assert result.requires_human_approval is True


def test_upfront_fee_is_rejected() -> None:
    result = evaluate_opportunity(
        Opportunity(
            title="Pay to qualify",
            opportunity_type="freelance_contract",
            summary="Claims paid work but requests a fee first.",
            payout_value_usd=5000,
            effort_hours=4,
            credibility_score=8,
            fit_score=9,
            urgency_score=8,
            eligibility_score=9,
            evidence=[official_evidence()],
            requires_upfront_payment=True,
        )
    )
    assert result.decision == "reject"
    assert "Requires upfront payment to qualify" in result.reasons


def test_social_only_claim_is_rejected_until_officially_verified() -> None:
    result = evaluate_opportunity(
        Opportunity(
            title="Unverified social bounty",
            opportunity_type="bounty",
            summary="Only a social post supports the payout claim.",
            payout_value_usd=15000,
            effort_hours=5,
            credibility_score=6,
            fit_score=10,
            urgency_score=9,
            eligibility_score=9,
            evidence=[
                Evidence(
                    source_url="https://example.com/social-post",
                    source_name="Social post",
                    official=False,
                )
            ],
        )
    )
    assert result.decision == "reject"
    assert "No official source has been verified" in result.reasons


def test_speculative_trading_is_rejected() -> None:
    result = evaluate_opportunity(
        Opportunity(
            title="Trading competition",
            opportunity_type="web3_paid_work",
            summary="Prize depends on speculative trading performance.",
            payout_value_usd=50000,
            effort_hours=10,
            evidence=[official_evidence()],
            is_speculative_trading=True,
        )
    )
    assert result.decision == "reject"
