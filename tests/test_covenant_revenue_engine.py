from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest

from aion.covenant import CovenantError, CovenantRuntime
from aion.opportunity_store import OpportunityStore
from aion.revenue_engine import build_opportunity, rank_opportunities


def test_covenant_requires_secret() -> None:
    with pytest.raises(CovenantError):
        CovenantRuntime.from_env({})


def test_covenant_integrity_and_emissary_capsule_do_not_expose_text() -> None:
    text = "PRIVATE COVENANT CONTENT"
    encoded = base64.b64encode(text.encode()).decode()
    digest = hashlib.sha256(text.encode()).hexdigest()
    covenant = CovenantRuntime.from_env(
        {
            "AION_COVENANT_B64": encoded,
            "AION_COVENANT_SHA256": digest,
            "AION_COVENANT_ID": "AION-COVENANT-001",
            "AION_COVENANT_PRINCIPAL": "YALEEL-VERIFIED",
        }
    )
    capsule = covenant.emissary_capsule(role="revenue_emissary")
    assert capsule["covenant"] == "AION-COVENANT-001"
    assert capsule["disclosure"] == "PROHIBITED"
    assert text not in str(capsule)
    assert digest not in str(capsule)


def test_covenant_rejects_integrity_mismatch() -> None:
    text = "PRIVATE"
    encoded = base64.b64encode(text.encode()).decode()
    with pytest.raises(CovenantError, match="integrity"):
        CovenantRuntime.from_env(
            {
                "AION_COVENANT_B64": encoded,
                "AION_COVENANT_SHA256": "0" * 64,
            }
        )


def test_revenue_engine_ranks_evidence_weighted_durable_value() -> None:
    strong = build_opportunity(
        scout="commercial",
        source="public-request-1",
        customer_problem="Broken production website",
        proposed_solution="Website repair",
        estimated_revenue=500,
        estimated_cost=25,
        probability=0.65,
        capital_required=0,
        time_hours=2,
        confidence=0.9,
        next_action="Prepare owner-reviewed outreach",
    )
    hype = build_opportunity(
        scout="web",
        source="speculative-thread",
        customer_problem="Unverified market rumor",
        proposed_solution="Speculative product",
        estimated_revenue=5000,
        estimated_cost=1000,
        probability=0.08,
        capital_required=1000,
        time_hours=20,
        confidence=0.2,
        next_action="Research evidence before any action",
    )
    ranked = rank_opportunities([hype, strong])
    assert ranked[0].opportunity_id == strong.opportunity_id


def test_opportunity_store_persists_and_records_realized_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    path = str(tmp_path / "opportunities.db")
    store = OpportunityStore(path)
    opportunity = build_opportunity(
        scout="agent_network",
        source="moltbook:post:123",
        customer_problem="Agent needs a deployment diagnostic",
        proposed_solution="YaliTek Emergency Diagnostic",
        estimated_revenue=149,
        probability=0.5,
        confidence=0.75,
        next_action="Request owner approval before outreach",
    )
    store.upsert(opportunity)
    rows = store.top()
    assert rows[0]["authorization_required"] == "owner_before_transaction"
    store.record_result(opportunity.opportunity_id, result="paid", realized_value=149)
    rows = store.top()
    assert rows[0]["actual_result"] == "paid"
    assert rows[0]["realized_value"] == 149
    store.close()
