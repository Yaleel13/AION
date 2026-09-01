"""Payment fulfillment and order lifecycle management.

Processes completed payment orders and updates opportunity ledger with
realized revenue. Fulfillment remains owner-gated: automatic actions are
disabled until explicit authorization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aion.opportunity_store import OpportunityStore


def process_completed_payment_order(
    store: OpportunityStore,
    order_id: str,
    commercial_execution_id: str = "",
) -> dict[str, Any]:
    """Mark a payment order as fulfilled and update opportunity ledger.

    Args:
        store: OpportunityStore instance for durable updates
        order_id: Unique payment order identifier
        commercial_execution_id: Optional ID of commercial execution that generated this revenue

    Returns:
        Dictionary with fulfillment status and side-effects applied
    """
    orders = store.list_payment_orders()
    order = None
    for row in orders:
        if str(row.get("order_id") or "") == order_id:
            order = row
            break

    if not order:
        raise ValueError(f"Order {order_id} not found")

    status = str(order.get("status") or "unknown")
    opportunity_id = str(order.get("opportunity_id") or "")
    realized_value = float(order.get("amount_cents") or 0) / 100.0

    if status == "paid":
        # Update opportunity with realized value
        store.record_result(
            opportunity_id,
            result="payment_received_and_fulfilled",
            realized_value=realized_value,
        )
        # Mark order as fulfilled
        store._conn.execute(
            "UPDATE payment_orders SET status = ?, updated_at = ? WHERE order_id = ? AND status = ?",
            ("fulfilled", datetime.now(timezone.utc).isoformat(), order_id, "paid"),
        )
        store._conn.commit()

        # Record revenue attribution if commercial execution ID provided
        if commercial_execution_id:
            store.record_revenue_attribution(
                order_id=order_id,
                opportunity_id=opportunity_id,
                commercial_execution_id=commercial_execution_id,
            )

        return {
            "status": "success",
            "order_id": order_id,
            "opportunity_id": opportunity_id,
            "realized_value": realized_value,
            "fulfillment_action": "payment_received_and_fulfilled",
            "attributed_to": commercial_execution_id or None,
            "note": "Opportunity marked as paid and resolved in ledger.",
        }

    if status == "pending_owner_approval":
        return {
            "status": "pending",
            "order_id": order_id,
            "opportunity_id": opportunity_id,
            "reason": "Order is awaiting owner approval before fulfillment",
            "action_required": "owner_should_approve",
        }

    return {
        "status": "no_action",
        "order_id": order_id,
        "opportunity_id": opportunity_id,
        "current_status": status,
        "reason": f"Order status {status} does not require fulfillment processing",
    }


def fulfill_paid_orders(store: OpportunityStore) -> list[dict[str, Any]]:
    """Fulfill all paid orders awaiting fulfillment.

    Args:
        store: OpportunityStore instance for durable updates

    Returns:
        List of fulfillment results
    """
    orders = store.list_payment_orders()
    results = []
    for order in orders:
        status = str(order.get("status") or "unknown")
        order_id = str(order.get("order_id") or "")
        if status == "paid" and order_id:
            result = process_completed_payment_order(store, order_id)
            results.append(result)
    return results
