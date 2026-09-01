from __future__ import annotations

import hashlib
import hmac
import json

from aion.opportunity_store import OpportunityStore
from aion.stripe_runtime import StripeRuntime, build_stripe_signature


def test_stripe_runtime_is_not_ready_until_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_CHECKOUT_ENABLED", raising=False)
    runtime = StripeRuntime()
    assert runtime.is_configured() is False
    assert runtime.is_ready_for_checkout() is False


def test_stripe_signature_verifies_valid_signed_payload(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "supersecret")
    payload = json.dumps({"type": "checkout.session.completed", "id": "cs_test_123"}).encode()
    timestamp = "1700000000"
    signature = build_stripe_signature(payload, timestamp, "supersecret")
    header = f"t={timestamp},v1={signature}"

    assert StripeRuntime().verify_webhook_signature(payload, header) is True


def test_stripe_signature_rejects_tampered_payload(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "supersecret")
    payload = json.dumps({"type": "checkout.session.completed", "id": "cs_test_123"}).encode()
    timestamp = "1700000000"
    valid = build_stripe_signature(payload, timestamp, "supersecret")
    bad_payload = json.dumps({"type": "checkout.session.completed", "id": "cs_test_456"}).encode()
    bad_header = f"t={timestamp},v1={valid}"

    assert StripeRuntime().verify_webhook_signature(bad_payload, bad_header) is False


def test_stripe_runtime_builds_checkout_payload_when_ready(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    runtime = StripeRuntime()
    payload = runtime.create_checkout_session_payload(
        amount_cents=1500,
        currency="usd",
        success_url="https://example.com/success",
        order_id="order_123",
    )

    assert runtime.is_ready_for_checkout() is True
    assert payload["mode"] == "payment"
    assert payload["success_url"].endswith("/success")
    assert payload["metadata"]["order_id"] == "order_123"


def test_opportunity_store_records_payment_order_in_ledger(tmp_path) -> None:
    store = OpportunityStore(str(tmp_path / "payments.db"))
    order = store.record_payment_order(
        order_id="order_123",
        opportunity_id="opp_abc",
        amount_cents=1500,
        currency="usd",
        customer_email="buyer@example.com",
    )

    rows = store.list_payment_orders()
    assert len(rows) == 1
    assert rows[0]["status"] == "pending_owner_approval"
    assert rows[0]["order_id"] == "order_123"
    assert order["status"] == "pending_owner_approval"
