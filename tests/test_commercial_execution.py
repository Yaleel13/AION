from __future__ import annotations

from aion.commercial_execution import build_commercial_execution_plan, propose_commercial_execution
from aion.moltbook.approval import Phase2ApprovalGate
from aion.moltbook.security import KillSwitch
from aion.moltbook.store import Phase2Store


def _row(**overrides):
    row = {
        "opportunity_id": "opp-commercial-1",
        "scout": "agent_network",
        "source": "https://www.moltbook.com/post/abc123",
        "customer_problem": "Need website repair and deployment help; budget $2,000",
        "proposed_solution": "Evaluate fit to an existing YaliTek service and prepare owner-reviewed outreach",
        "estimated_revenue": 2000.0,
        "estimated_cost": 100.0,
        "probability": 0.7,
        "expected_value": 1330.0,
        "capital_required": 0.0,
        "time_hours": 2.0,
        "major_risks": "Verify buyer identity and scope.",
        "ethical_considerations": "No deceptive claims.",
        "confidence": 0.9,
        "durable_value_score": 1.0,
        "next_action": "Verify source and prepare owner-reviewed response",
        "authorization_required": "owner_before_transaction",
        "actual_result": "unresolved",
        "realized_value": 0.0,
    }
    row.update(overrides)
    return row


def test_moltbook_commercial_opportunity_can_prepare_exact_comment():
    plan = build_commercial_execution_plan(_row())
    assert plan.executable is True
    assert plan.channel == "moltbook_public_comment"
    assert plan.destination == "post:abc123"
    assert plan.payload["post_id"] == "abc123"
    assert "budget" in plan.payload["content"].lower()


def test_external_commercial_source_remains_preparation_only():
    plan = build_commercial_execution_plan(
        _row(source="https://example.com/opportunity/1")
    )
    assert plan.executable is False
    assert plan.channel == "preparation_only"
    assert "No reviewed executable channel" in plan.reason


def test_grants_and_bids_cannot_use_commercial_executor():
    grant = build_commercial_execution_plan(
        _row(authorization_required="owner_before_application")
    )
    bid = build_commercial_execution_plan(
        _row(authorization_required="owner_before_bid")
    )
    assert grant.executable is False
    assert bid.executable is False


def test_verify_before_pursuit_is_not_executable():
    plan = build_commercial_execution_plan(
        _row(estimated_revenue=0.0, expected_value=0.0)
    )
    assert plan.executable is False
    assert "pursue_owner_review" in plan.reason


def test_prepare_creates_owner_approval_without_execution(tmp_path):
    store = Phase2Store(str(tmp_path / "phase2.sqlite3"))
    gate = Phase2ApprovalGate(
        store,
        kill_switch=KillSwitch(False, "test"),
        token_pepper="test-pepper",
    )
    result = propose_commercial_execution(_row(), gate)
    assert result["created"] is True
    approval = result["approval"]
    assert approval["decision"] == "pending"
    assert approval["action"] == "comment"
    assert approval["destination"] == "post:abc123"
    assert approval["executed_at"] is None
    assert approval["token_consumed_at"] is None


def test_prepare_is_idempotent_for_same_opportunity(tmp_path):
    store = Phase2Store(str(tmp_path / "phase2.sqlite3"))
    gate = Phase2ApprovalGate(
        store,
        kill_switch=KillSwitch(False, "test"),
        token_pepper="test-pepper",
    )
    first = propose_commercial_execution(_row(), gate)
    second = propose_commercial_execution(_row(), gate)
    assert first["approval"]["request_id"] == second["approval"]["request_id"]
