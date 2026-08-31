from __future__ import annotations

from datetime import datetime, timezone

from aion.opportunity_qualification import qualify_opportunity, qualify_ranked


def _row(**overrides):
    base = {
        "opportunity_id": "opp_test",
        "customer_problem": "Need AI automation and website deployment support",
        "proposed_solution": "YaliTek automation and hosting support",
        "major_risks": "",
        "ethical_considerations": "",
        "next_action": "Review scope",
        "source": "https://example.com/opportunity",
        "time_hours": 4,
        "expected_value": 1200,
        "estimated_revenue": 1500,
        "capital_required": 100,
        "confidence": 0.8,
        "probability": 0.55,
    }
    base.update(overrides)
    return base


def test_capability_fit_supports_existing_yalitek_services() -> None:
    q = qualify_opportunity(_row())
    assert q.capability_fit > 0
    assert "ai" in q.capability_matches
    assert "automation" in q.capability_matches
    assert "hosting" in q.capability_matches


def test_unknown_federal_eligibility_remains_unknown() -> None:
    q = qualify_opportunity(
        _row(
            customer_problem="Federal contract opportunity for information technology small business set-aside",
            source="https://sam.gov/opportunities/123",
        ),
        environ={},
    )
    assert q.eligibility_status == "unknown_requires_verification"
    assert "eligibility not verified" in q.blockers
    assert "SAM registration status" in q.unknowns
    assert "small-business/set-aside eligibility" in q.unknowns
    assert q.recommendation == "verify_before_pursuit"


def test_owner_verified_eligibility_can_be_used_as_evidence() -> None:
    q = qualify_opportunity(
        _row(
            customer_problem="Federal contract opportunity for information technology small business",
            source="https://sam.gov/opportunities/123",
        ),
        environ={
            "AION_SAM_REGISTERED": "true",
            "AION_SMALL_BUSINESS_VERIFIED": "true",
        },
    )
    assert q.eligibility_status == "verified_for_known_requirements"
    assert len(q.eligibility_evidence) == 2


def test_expired_deadline_blocks_pursuit() -> None:
    q = qualify_opportunity(
        _row(next_action="Deadline: 2026-08-01"),
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    assert q.deadline_status == "expired"
    assert q.recommendation == "do_not_pursue"


def test_unknown_revenue_requires_verification() -> None:
    q = qualify_opportunity(_row(estimated_revenue=0, expected_value=0))
    assert "commercial value/revenue" in q.unknowns
    assert q.recommendation == "verify_before_pursuit"


def test_no_capability_match_is_not_recommended() -> None:
    q = qualify_opportunity(
        _row(
            customer_problem="Marine excavation and bridge demolition contract",
            proposed_solution="Review opportunity",
        ),
        environ={},
    )
    assert q.capability_fit == 0
    assert q.recommendation == "do_not_pursue"


def test_qualified_ranking_uses_pursuit_score() -> None:
    strong = _row(opportunity_id="strong")
    weak = _row(
        opportunity_id="weak",
        customer_problem="Unknown general business opportunity",
        proposed_solution="Research",
        estimated_revenue=0,
        expected_value=0,
        confidence=0.3,
        probability=0.1,
    )
    rows = qualify_ranked([weak, strong])
    assert rows[0]["opportunity_id"] == "strong"
    assert rows[0]["qualification"]["pursue_score"] >= rows[1]["qualification"]["pursue_score"]
