"""Stripe runtime guardrails.

This module is intentionally fail-closed: it does not create payments or execute
financial actions unless the owner explicitly enables the Stripe integration and
provides the required secrets.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore[assignment]
    STRIPE_AVAILABLE = False


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def build_stripe_signature(payload: bytes, timestamp: str, secret: str) -> str:
    """Build the Stripe v1 signature for a signed webhook payload."""
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    return hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _metadata_value(value: Any, *, limit: int = 500) -> str:
    """Normalize one Stripe metadata value without leaking arbitrary objects."""
    text = str(value or "").strip()
    return text[:limit]


def _clean_product_name(value: Any) -> str:
    """Return a bounded canonical checkout label, never arbitrary buyer text."""
    text = str(value or "AION service").strip() or "AION service"
    return text[:120]


class StripeRuntime:
    """Safety-gated Stripe adapter.

    By default this adapter is inert and never creates or mutates financial state.
    The owner must opt in via STRIPE_CHECKOUT_ENABLED and provide valid Stripe
    secrets before the runtime becomes operational.
    """

    def __init__(self) -> None:
        self.secret_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
        self.webhook_secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
        self.checkout_enabled = _env_truthy("STRIPE_CHECKOUT_ENABLED")
        self.client = None

    def _client(self):
        """Create the scoped Stripe client only when an API request is required."""
        if self.client is not None:
            return self.client
        if not STRIPE_AVAILABLE:
            raise RuntimeError("stripe package is not installed")
        if not self.secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured")
        self.client = stripe.StripeClient(self.secret_key)
        return self.client

    def is_configured(self) -> bool:
        return bool(self.secret_key) and bool(self.webhook_secret)

    def readiness(self) -> dict[str, bool]:
        """Return non-secret readiness signals for truthful runtime diagnostics."""
        return {
            "checkout_enabled": bool(self.checkout_enabled),
            "secret_key_present": bool(self.secret_key),
            "webhook_secret_present": bool(self.webhook_secret),
            "stripe_package_available": bool(STRIPE_AVAILABLE),
            "ready_for_checkout": bool(self.checkout_enabled and self.is_configured() and STRIPE_AVAILABLE),
        }

    def is_ready_for_checkout(self) -> bool:
        return self.readiness()["ready_for_checkout"]

    def verify_webhook_signature(self, payload: bytes, header: str, *, tolerance_seconds: int = 300) -> bool:
        if not self.webhook_secret or not header:
            return False

        parts = [part.strip() for part in header.split(",")]
        timestamp = None
        signatures: list[str] = []
        for part in parts:
            if part.startswith("t="):
                timestamp = part.split("=", 1)[1]
            elif part.startswith("v1="):
                signatures.append(part.split("=", 1)[1])
        if not timestamp or not signatures:
            return False

        try:
            signed_at = int(timestamp)
        except ValueError:
            return False
        if abs(int(time.time()) - signed_at) > max(0, int(tolerance_seconds)):
            return False

        expected = build_stripe_signature(payload, timestamp, self.webhook_secret)
        return any(hmac.compare_digest(expected, signature) for signature in signatures)

    def safe_checkout_params(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        product_name: str = "AION service",
    ) -> dict[str, Any]:
        if not self.is_ready_for_checkout():
            state = self.readiness()
            missing = [key for key, present in state.items() if key != "ready_for_checkout" and not present]
            raise RuntimeError("Stripe checkout is not ready: " + ", ".join(missing or ["unknown configuration error"]))
        if amount_cents <= 0:
            raise ValueError("amount_cents must be positive")
        currency = str(currency or "").strip().lower()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a 3-letter ISO currency code")
        success_url = str(success_url or "").strip()
        if not success_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("success_url must be an approved http(s) URL")

        return {
            "mode": "payment",
            "line_items": [
                {
                    "price_data": {
                        "currency": currency,
                        "unit_amount": int(amount_cents),
                        "product_data": {"name": _clean_product_name(product_name)},
                    },
                    "quantity": 1,
                }
            ],
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
        opportunity_id: str,
        customer_email: str | None = None,
        commercial_execution_id: str = "",
        lead_id: str = "",
        product_key: str = "",
        source_post_id: str = "",
        source_url: str = "",
        venture: str = "",
        product_name: str = "AION service",
    ) -> dict[str, Any]:
        params = self.safe_checkout_params(
            amount_cents=amount_cents,
            currency=currency,
            success_url=success_url,
            product_name=product_name,
        )
        params["metadata"] = {
            "order_id": _metadata_value(order_id),
            "opportunity_id": _metadata_value(opportunity_id),
            "commercial_execution_id": _metadata_value(commercial_execution_id),
            "lead_id": _metadata_value(lead_id),
            "product_key": _metadata_value(product_key),
            "source_post_id": _metadata_value(source_post_id),
            "source_url": _metadata_value(source_url),
            "venture": _metadata_value(venture),
            "source": "aion-attributed-checkout",
        }
        params["integration_identifier"] = "aion_checkout_kqzmxpvn"
        if customer_email:
            params["customer_email"] = str(customer_email).strip()
        return params

    def create_checkout_session(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        order_id: str,
        opportunity_id: str,
        customer_email: str | None = None,
        commercial_execution_id: str = "",
        lead_id: str = "",
        product_key: str = "",
        source_post_id: str = "",
        source_url: str = "",
        venture: str = "",
        product_name: str = "AION service",
    ) -> dict[str, Any]:
        """Create a live Stripe checkout session with end-to-end attribution metadata."""
        if not self.is_ready_for_checkout():
            state = self.readiness()
            missing = [key for key, present in state.items() if key != "ready_for_checkout" and not present]
            raise RuntimeError("Stripe checkout is not ready: " + ", ".join(missing or ["unknown configuration error"]))

        params = self.create_checkout_session_payload(
            amount_cents=amount_cents,
            currency=currency,
            success_url=success_url,
            order_id=order_id,
            opportunity_id=opportunity_id,
            customer_email=customer_email,
            commercial_execution_id=commercial_execution_id,
            lead_id=lead_id,
            product_key=product_key,
            source_post_id=source_post_id,
            source_url=source_url,
            venture=venture,
            product_name=product_name,
        )

        try:
            session = self._client().v1.checkout.sessions.create(params)
            session_id = str(getattr(session, "id", "") or "").strip()
            checkout_url = str(getattr(session, "url", "") or "").strip()
            if not session_id or not checkout_url:
                raise RuntimeError("Stripe returned a Checkout Session without id/url")
            return {"session_id": session_id, "checkout_url": checkout_url}
        except RuntimeError:
            raise
        except Exception as exc:
            if STRIPE_AVAILABLE and hasattr(stripe, "error") and isinstance(exc, stripe.error.StripeError):
                user_message = getattr(exc, "user_message", None)
                raise RuntimeError(f"Stripe API error: {user_message or str(exc)}") from exc
            raise RuntimeError(f"Stripe checkout session creation failed: {str(exc)}") from exc
