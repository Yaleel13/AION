from __future__ import annotations

from pathlib import Path

from opportunity_operator.adapters import SourceRecord, normalize_record, parse_deadline
from opportunity_operator.models import Evidence, Opportunity
from opportunity_operator.persistent_ledger import JsonOpportunityLedger
from opportunity_operator.pipeline import process_candidates


def test_deadline_normalizes_to_utc():
    value = parse_deadline("2026-09-14T17:00:00-07:00")
    assert value is not None
    assert value.isoformat() == "2026-09-15T00:00:00+00:00"


def test_source_record_becomes_opportunity_with_provenance():
    opportunity = normalize_record(
        SourceRecord(
            source_name="Official sponsor",
            source_url="https://example.org/opportunity",
            official=True,
            payload={
                "title": "Verified agent challenge",
                "opportunity_type": "hackathon",
                "summary": "A legitimate agent challenge.",
                "payout_value_usd": 10000,
                "effort_hours": 20,
                "deadline": "2026-09-14T20:00:00Z",
                "eligibility_score": 9,
                "credibility_score": 10,
                "fit_score": 10,
                "urgency_score": 9,
            },
        )
    )
    assert opportunity.title == "Verified agent challenge"
    assert opportunity.evidence[0].official is True
    assert opportunity.deadline is not None


def test_persistent_ledger_silences_unchanged_after_reload(tmp_path: Path):
    ledger_path = tmp_path / "ledger.json"
    opportunity = Opportunity(
        title="Verified grant",
        opportunity_type="grant",
        summary="Verified grant opportunity",
        payout_value_usd=25000,
        effort_hours=10,
        eligibility_score=9,
        credibility_score=10,
        fit_score=9,
        urgency_score=8,
        evidence=[
            Evidence(
                source_url="https://example.org/grant",
                source_name="Official grant page",
                official=True,
            )
        ],
    )

    first = JsonOpportunityLedger(ledger_path)
    results = process_candidates([opportunity], first)
    assert len(results) == 1
    assert ledger_path.exists()

    reloaded = JsonOpportunityLedger(ledger_path)
    assert process_candidates([opportunity], reloaded) == []
