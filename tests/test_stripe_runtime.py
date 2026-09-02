from __future__ import annotations

import hashlib
import hmac
import json
import time
from types import SimpleNamespace

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
    timestamp = str(int(time.time()))
    signature = build_stripe_signature(payload, timestamp, "supersecret")
    header = f"t={timestamp},v1={signature}"

    assert StripeRuntime().verify_webhook_signature(payload, header) is True


def test_stripe_signature_rejects_tampered_payload(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "supersecret")
    payload = json.dumps({"type": "checkout.session.completed", "id": "cs_test_123"}).encode()
    timestamp = str(int(time.time()))
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
        opportunity_id="opp_123",
        commercial_execution_id="exec_123",
        lead_id="lead_123",
        product_key="quick-tech-diagnostic",
        source_post_id="post_123",
        source_url="https://www.moltbook.com/post/post_123",
        venture="YaliTek Online",
    )

    assert runtime.is_ready_for_checkout() is True
    assert payload["mode"] == "payment"
    assert payload["success_url"].endswith("/success")
    assert payload["metadata"]["order_id"] == "order_123"
    assert payload["metadata"]["opportunity_id"] == "opp_123"
    assert payload["metadata"]["commercial_execution_id"] == "exec_123"
    assert payload["metadata"]["lead_id"] == "lead_123"
    assert payload["metadata"]["product_key"] == "quick-tech-diagnostic"
    assert payload["metadata"]["source_post_id"] == "post_123"
    assert payload["metadata"]["source_url"] == "https://www.moltbook.com/post/post_123"
    assert payload["metadata"]["venture"] == "YaliTek Online"
    assert payload["metadata"]["source"] == "aion-attributed-checkout"
    assert payload["integration_identifier"] == "aion_checkout_kqzmxpvn"


def test_stripe_runtime_uses_scoped_client_for_checkout(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "rk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")
    calls: list[dict] = []

    class FakeSessions:
        def create(self, params):
            calls.append(params)
            return SimpleNamespace(id="cs_test_scoped", url="https://checkout.stripe.test/session")

    runtime = StripeRuntime()
    runtime.client = SimpleNamespace(
        v1=SimpleNamespace(checkout=SimpleNamespace(sessions=FakeSessions()))
    )

    result = runtime.create_checkout_session(
        amount_cents=1500,
        currency="usd",
        success_url="https://example.com/success",
        order_id="order_123",
        opportunity_id="opp_123",
        commercial_execution_id="exec_123",
        lead_id="lead_123",
        product_key="quick-tech-diagnostic",
        source_post_id="post_123",
        source_url="https://www.moltbook.com/post/post_123",
        venture="YaliTek Online",
    )

    assert result["session_id"] == "cs_test_scoped"
    assert calls[0]["integration_identifier"] == "aion_checkout_kqzmxpvn"
    assert calls[0]["metadata"]["commercial_execution_id"] == "exec_123"
    assert calls[0]["metadata"]["lead_id"] == "lead_123"
    assert calls[0]["metadata"]["product_key"] == "quick-tech-diagnostic"
    assert calls[0]["metadata"]["source_post_id"] == "post_123"


def test_stripe_metadata_values_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    payload = StripeRuntime().create_checkout_session_payload(
        amount_cents=1500,
        currency="usd",
        success_url="https://example.com/success",
        order_id="order_123",
        opportunity_id="opp_123",
        source_url="x" * 1000,
    )
    assert len(payload["metadata"]["source_url"]) == 500


def test_stripe_signature_rejects_stale_signed_payload(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "supersecret")
    payload = json.dumps({"type": "checkout.session.completed", "id": "evt_old"}).encode()
    timestamp = str(int(time.time()) - 301)
    signature = build_stripe_signature(payload, timestamp, "supersecret")

    assert StripeRuntime().verify_webhook_signature(payload, f"t={timestamp},v1={signature}") is False


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
