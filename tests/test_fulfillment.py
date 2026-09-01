"""Tests for payment fulfillment and order lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from aion.fulfillment import fulfill_paid_orders, process_completed_payment_order
from aion.opportunity_store import OpportunityStore
from aion.revenue_engine import build_opportunity


def test_process_completed_payment_order_marks_as_fulfilled(tmp_path: Path) -> None:
    store = OpportunityStore(str(tmp_path / "fulfillment.db"))

    # Create an opportunity first
    opp = build_opportunity(
        scout="web",
        source="test-site",
        customer_problem="Need solution",
        proposed_solution="Sell them one",
        estimated_revenue=1500.0,
        probability=0.8,
        confidence=0.6,
        next_action="Finalize sale",
    )
    store.upsert(opp)

    # Record a paid payment order
    order = store.record_payment_order(
        order_id="order_123",
        opportunity_id=opp.opportunity_id,
        amount_cents=1500,
        currency="usd",
        customer_email="buyer@example.com",
        status="paid",
    )

    assert order["status"] == "paid"

    # Process fulfillment
    result = process_completed_payment_order(store, "order_123")
    assert result["status"] == "success"
    assert result["realized_value"] == 15.0
    assert result["fulfillment_action"] == "payment_received_and_fulfilled"

    # Verify order was marked fulfilled
    updated = store.list_payment_orders()
    assert updated[0]["status"] == "fulfilled"

    # Verify opportunity was updated with realized value
    opps = store.top()
    found = None
    for opp_row in opps:
        if str(opp_row.get("opportunity_id") or "") == opp.opportunity_id:
            found = opp_row
            break
    assert found
    assert float(found.get("realized_value") or 0) == 15.0
    assert str(found.get("actual_result") or "") == "payment_received_and_fulfilled"


def test_fulfill_paid_orders_batch_processes(tmp_path: Path) -> None:
    store = OpportunityStore(str(tmp_path / "batch_fulfill.db"))

    opp1 = build_opportunity(
        scout="web",
        source="site-a",
        customer_problem="Need X",
        proposed_solution="Offer X",
        estimated_revenue=1000.0,
        probability=0.7,
        confidence=0.5,
        next_action="Close",
    )
    opp2 = build_opportunity(
        scout="web",
        source="site-b",
        customer_problem="Need Y",
        proposed_solution="Offer Y",
        estimated_revenue=2000.0,
        probability=0.8,
        confidence=0.6,
        next_action="Close",
    )
    store.upsert(opp1)
    store.upsert(opp2)

    # Create two paid orders
    store.record_payment_order(
        order_id="order_paid_1",
        opportunity_id=opp1.opportunity_id,
        amount_cents=1000,
        currency="usd",
        status="paid",
    )
    store.record_payment_order(
        order_id="order_paid_2",
        opportunity_id=opp2.opportunity_id,
        amount_cents=2000,
        currency="usd",
        status="paid",
    )

    # Create one pending order (should not be fulfilled)
    store.record_payment_order(
        order_id="order_pending",
        opportunity_id=opp1.opportunity_id,
        amount_cents=5000,
        currency="usd",
        status="pending_owner_approval",
    )

    # Fulfill all paid orders
    results = fulfill_paid_orders(store)
    assert len(results) == 2
    assert all(r["status"] == "success" for r in results)
    assert results[0]["realized_value"] == 10.0
    assert results[1]["realized_value"] == 20.0

    # Verify pending order is still pending
    orders = store.list_payment_orders()
    pending = [o for o in orders if str(o.get("order_id") or "") == "order_pending"]
    assert pending[0]["status"] == "pending_owner_approval"


def test_process_payment_order_not_yet_paid(tmp_path: Path) -> None:
    store = OpportunityStore(str(tmp_path / "not_paid.db"))

    opp = build_opportunity(
        scout="web",
        source="test",
        customer_problem="Need it",
        proposed_solution="Sell it",
        estimated_revenue=500.0,
        probability=0.9,
        confidence=0.7,
        next_action="Wait for payment",
    )
    store.upsert(opp)

    order = store.record_payment_order(
        order_id="order_pending_x",
        opportunity_id=opp.opportunity_id,
        amount_cents=500,
        currency="usd",
        status="pending_owner_approval",
    )

    result = process_completed_payment_order(store, "order_pending_x")
    assert result["status"] == "pending"
    assert result["action_required"] == "owner_should_approve"
