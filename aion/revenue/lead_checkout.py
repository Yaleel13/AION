"""Lead-specific Stripe Checkout creation for qualified public buyer intent.

This helper is intentionally narrow. It only creates a live Checkout Session for
creator-authorized products with a verified fixed price. It does not charge a
customer; the buyer must explicitly open Stripe Checkout and complete payment.
"""

from __future__ import annotations

import hashlib
from typing import Any

from aion.opportunity_store import OpportunityStore
from aion.stripe_runtime import StripeRuntime


_FIXED_PRICE_PRODUCTS: dict[str, dict[str, Any]] = {
    "quick-tech-diagnostic": {
        "amount_cents": 4900,
        "currency": "usd",
        "product_name": "YaliTek Quick Tech Diagnostic",
        "success_url": "https://yalitekonline.com",
    },
}


def _stable_token(value: str, *, length: int = 20) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def prepare_lead_checkout(
    *,
    lead: dict[str, Any],
    product: Any,
    store: OpportunityStore,
) -> dict[str, Any]:
    """Create one attributable Checkout Session for an eligible qualified lead.

    Returns a structured non-throwing result so the revenue cycle can fall back to
    the catalog's shared verified checkout URL when Stripe is unavailable.
    """
    fixed = _FIXED_PRICE_PRODUCTS.get(str(getattr(product, "product_key", "") or ""))
    if not fixed:
        return {"created": False, "reason": "product_not_fixed_price"}

    runtime = StripeRuntime()
    if not runtime.is_ready_for_checkout():
        return {"created": False, "reason": "stripe_not_ready"}

    post_id = str(lead.get("source_post_id") or "").strip()
    lead_id = str(lead.get("lead_id") or "").strip()
    source_url = str(lead.get("source_url") or "").strip()
    if not post_id or not lead_id:
        return {"created": False, "reason": "missing_attribution_ids"}

    fingerprint = _stable_token(f"moltbook:{post_id}:{lead_id}:{product.product_key}")
    opportunity_id = f"moltbook-{fingerprint}"
    order_id = f"order-{fingerprint}"
    commercial_execution_id = f"moltbook-convert-{post_id}"

    existing = next(
        (
            order
            for order in store.list_payment_orders(limit=200)
            if str(order.get("order_id") or "") == order_id
            and str(order.get("stripe_checkout_url") or "").strip()
        ),
        None,
    )
    if existing:
        return {
            "created": False,
            "reused": True,
            "checkout_url": existing["stripe_checkout_url"],
            "order_id": order_id,
            "opportunity_id": opportunity_id,
            "commercial_execution_id": commercial_execution_id,
        }

    store.record_payment_order(
        order_id=order_id,
        opportunity_id=opportunity_id,
        amount_cents=int(fixed["amount_cents"]),
        currency=str(fixed["currency"]),
        status="pending",
        commercial_execution_id=commercial_execution_id,
    )

    try:
        session = runtime.create_checkout_session(
            amount_cents=int(fixed["amount_cents"]),
            currency=str(fixed["currency"]),
            success_url=str(fixed["success_url"]),
            order_id=order_id,
            opportunity_id=opportunity_id,
            commercial_execution_id=commercial_execution_id,
            lead_id=lead_id,
            product_key=str(product.product_key),
            source_post_id=post_id,
            source_url=source_url,
            venture=str(product.venture),
        )
    except Exception as exc:  # fail soft; static verified checkout remains available
        return {"created": False, "reason": "stripe_session_error", "error": str(exc)[:200]}

    store._conn.execute(
        "UPDATE payment_orders SET stripe_session_id = ?, stripe_checkout_url = ? WHERE order_id = ?",
        (session["session_id"], session["checkout_url"], order_id),
    )
    store._conn.commit()
    return {
        "created": True,
        "checkout_url": session["checkout_url"],
        "session_id": session["session_id"],
        "order_id": order_id,
        "opportunity_id": opportunity_id,
        "commercial_execution_id": commercial_execution_id,
        "product_key": str(product.product_key),
        "lead_id": lead_id,
        "source_post_id": post_id,
    }
