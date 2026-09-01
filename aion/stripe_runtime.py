"""Stripe runtime guardrails.

This module is intentionally fail-closed: it does not create payments or execute
financial actions unless the owner explicitly enables the Stripe integration and
provides the required secrets.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def build_stripe_signature(payload: bytes, timestamp: str, secret: str) -> str:
    """Build the Stripe v1 signature for a signed webhook payload."""
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    return hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()


class StripeRuntime:
    """Safety-gated Stripe adapter.

    By default this adapter is inert and never creates or mutates financial state.
    The owner must opt in via STRIPE_CHECKOUT_ENABLED and provide a valid secret
    before the runtime becomes operational.
    """

    def __init__(self) -> None:
        self.secret_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
        self.webhook_secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
        self.checkout_enabled = _env_truthy("STRIPE_CHECKOUT_ENABLED")

        # Configure Stripe client if available and secret key is set
        if STRIPE_AVAILABLE and self.secret_key:
            stripe.api_key = self.secret_key

    def is_configured(self) -> bool:
        return bool(self.secret_key) and bool(self.webhook_secret)

    def is_ready_for_checkout(self) -> bool:
        return self.checkout_enabled and self.is_configured()

    def verify_webhook_signature(self, payload: bytes, header: str) -> bool:
        if not self.webhook_secret:
            return False
        if not header:
            return False

        parts = [part.strip() for part in header.split(",")]
        timestamp = None
        signature = None
        for part in parts:
            if part.startswith("t="):
                timestamp = part.split("=", 1)[1]
            elif part.startswith("v1="):
                signature = part.split("=", 1)[1]
        if not timestamp or not signature:
            return False

        expected = build_stripe_signature(payload, timestamp, self.webhook_secret)
        return hmac.compare_digest(expected, signature)

    def safe_checkout_params(self, *, amount_cents: int, currency: str, success_url: str) -> dict[str, Any]:
        if not self.is_ready_for_checkout():
            raise RuntimeError("Stripe checkout is disabled until STRIPE_CHECKOUT_ENABLED and secrets are configured")
        if amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        if not success_url:
            raise ValueError("success_url is required")
        return {
            "mode": "payment",
            "line_items": [{"price_data": {"currency": currency.lower(), "unit_amount": amount_cents, "product_data": {"name": "AION service"}}, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": success_url,
            "automatic_tax": {"enabled": False},
        }

    def create_checkout_session_payload(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        order_id: str,
        customer_email: str | None = None,
    ) -> dict[str, Any]:
        params = self.safe_checkout_params(
            amount_cents=amount_cents,
            currency=currency,
            success_url=success_url,
        )
        params["metadata"] = {
            "order_id": order_id,
            "customer_email": customer_email or "",
            "source": "aion-owner-approved-checkout",
        }
        return params

    def create_checkout_session(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        order_id: str,
        customer_email: str | None = None,
    ) -> dict[str, Any]:
        """Create a live Stripe checkout session.

        Returns dict with:
        - session_id: Stripe session ID
        - checkout_url: URL customer should visit to complete payment
        """
        if not self.is_ready_for_checkout():
            raise RuntimeError("Stripe checkout is disabled until STRIPE_CHECKOUT_ENABLED and secrets are configured")

        if not STRIPE_AVAILABLE:
            raise RuntimeError("stripe package not installed")

        params = self.safe_checkout_params(
            amount_cents=amount_cents,
            currency=currency,
            success_url=success_url,
        )
        params["metadata"] = {
            "order_id": order_id,
            "customer_email": customer_email or "",
            "source": "aion-owner-approved-checkout",
        }
        if customer_email:
            params["customer_email"] = customer_email

        try:
            session = stripe.checkout.Session.create(**params)
            return {
                "session_id": session.id,
                "checkout_url": session.url,
            }
        except stripe.error.StripeError as e:
            raise RuntimeError(f"Stripe API error: {e.user_message or str(e)}")
