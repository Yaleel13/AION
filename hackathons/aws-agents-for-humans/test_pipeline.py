from datetime import datetime, timezone

from opportunity_operator.models import Evidence, Opportunity
from opportunity_operator.pipeline import OpportunityLedger, process_candidates


def _verified(title: str = "Verified grant", payout: float = 5000) -> Opportunity:
    return Opportunity(
        title=title,
        opportunity_type="grant",
        summary="A verified funding opportunity.",
        payout_value_usd=payout,
        effort_hours=8,
        deadline=datetime(2026, 10, 1, tzinfo=timezone.utc),
        eligibility_score=8,
        credibility_score=9,
        fit_score=9,
        urgency_score=7,
        evidence=[
            Evidence(
                source_url="https://example.org/official-grant",
                source_name="Official grant page",
                official=True,
            )
        ],
    )


def test_unverified_social_discovery_is_rejected():
    ledger = OpportunityLedger()
    rumor = Opportunity(
        title="Social rumor",
        opportunity_type="grant",
        summary="Unverified social claim.",
        payout_value_usd=10000,
        effort_hours=2,
        eligibility_score=8,
        credibility_score=3,
        fit_score=8,
        urgency_score=7,
        evidence=[
            Evidence(
                source_url="https://www.reddit.com/r/example/comments/rumor",
                source_name="Reddit",
                official=False,
            )
        ],
    )
    [(state, packet)] = process_candidates([rumor], ledger)
    assert state == "new"
    assert packet.decision == "reject"
    assert any("official" in reason for reason in packet.reasons)


def test_unchanged_candidate_is_silent_after_first_run():
    ledger = OpportunityLedger()
    candidate = _verified()
    first = process_candidates([candidate], ledger)
    second = process_candidates([candidate], ledger)
    assert len(first) == 1
    assert second == []


def test_material_payout_change_is_reported():
    ledger = OpportunityLedger()
    original = _verified(payout=5000)
    changed = _verified(payout=7500)
    process_candidates([original], ledger)
    [(state, packet)] = process_candidates([changed], ledger)
    assert state == "materially_changed"
    assert packet.title == changed.title


def test_duplicate_in_same_batch_is_deduped():
    ledger = OpportunityLedger()
    candidate = _verified()
    processed = process_candidates([candidate, candidate], ledger)
    assert len(processed) == 1
