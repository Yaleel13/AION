"""Tests for AION FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from aion.main import app
from aion.rate_limit import ClientSlidingWindowRateLimiter
from aion.schemas import AIResponse

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["runtime"] == "agent-v1"
    assert "openai_configured" in data


@patch("aion.main.config.OPENAI_API_KEY", "test-key")
@patch("aion.main.run_aion", new_callable=AsyncMock)
def test_agent_endpoint(mock_run):
    mock_run.return_value = {
        "agent": "AION",
        "session_id": "test-session",
        "response": "Runtime operational.",
        "requires_approval": False,
        "usage": {
            "requests": 1,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
    }
    response = client.post(
        "/agent",
        json={"message": "Check your runtime status", "session_id": "test-session"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "AION"
    assert data["session_id"] == "test-session"
    assert data["response"] == "Runtime operational."
    assert data["requires_approval"] is False


def test_agent_endpoint_no_key():
    with patch("aion.main.config.OPENAI_API_KEY", ""):
        response = client.post("/agent", json={"message": "Hello"})
    assert response.status_code == 503


@patch("aion.main.config.OPENAI_API_KEY", "test-key")
@patch("aion.main.run_aion", new_callable=AsyncMock)
def test_agent_endpoint_rate_limit(mock_run):
    mock_run.return_value = {
        "agent": "AION",
        "session_id": "test-session",
        "response": "Runtime operational.",
        "requires_approval": False,
        "usage": {"requests": 1, "input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }
    with patch("aion.main.agent_rate_limiter", ClientSlidingWindowRateLimiter(1)):
        first_response = client.post("/agent", json={"message": "First request"})
        second_response = client.post("/agent", json={"message": "Second request"})

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.headers["retry-after"]


@patch("aion.main.config.OPENAI_API_KEY", "test-key")
@patch("aion.main.query_chatgpt", new_callable=AsyncMock)
def test_chatgpt_endpoint(mock_query):
    mock_query.return_value = AIResponse(
        provider="chatgpt",
        model="gpt-4o-mini",
        message="Hello",
        response="Hi there!",
    )
    response = client.post("/chatgpt", json={"message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "chatgpt"
    assert data["response"] == "Hi there!"


def test_chatgpt_endpoint_no_key():
    with patch("aion.main.config.OPENAI_API_KEY", ""):
        response = client.post("/chatgpt", json={"message": "Hello"})
    assert response.status_code == 503


@patch("aion.main.config.GEMINI_API_KEY", "test-key")
@patch("aion.main.query_gemini", new_callable=AsyncMock)
def test_gemini_endpoint(mock_query):
    mock_query.return_value = AIResponse(
        provider="gemini",
        model="gemini-1.5-flash",
        message="Hello",
        response="Greetings!",
    )
    response = client.post("/gemini", json={"message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "gemini"
    assert data["response"] == "Greetings!"


def test_gemini_endpoint_no_key():
    with patch("aion.main.config.GEMINI_API_KEY", ""):
        response = client.post("/gemini", json={"message": "Hello"})
    assert response.status_code == 503


def test_owner_prepares_checkout_when_stripe_enabled(monkeypatch):
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    response = client.post(
        "/owner/checkout/prepare",
        headers={"Authorization": "Bearer owner-token"},
        json={
            "order_id": "order_456",
            "opportunity_id": "opp_abc",
            "amount_cents": 1500,
            "currency": "USD",
            "customer_email": "buyer@example.com",
            "success_url": "https://example.com/success",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checkout"]["metadata"]["order_id"] == "order_456"
    assert data["order"]["status"] == "pending_owner_approval"


def test_owner_checkout_webhook_accepts_valid_signed_event(monkeypatch):
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "metadata": {"order_id": "order_789", "opportunity_id": "opp_abc"},
                "amount_total": 1500,
                "currency": "usd",
                "customer_details": {"email": "buyer@example.com"},
            }
        },
    }
    raw = __import__("json").dumps(payload).encode()
    timestamp = "1700000000"
    signature = __import__("hmac").new(
        b"whsec_123",
        f"{timestamp}.{raw.decode('utf-8')}".encode("utf-8"),
        __import__("hashlib").sha256,
    ).hexdigest()

    response = client.post(
        "/owner/checkout/webhook",
        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
        content=raw,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["event_type"] == "checkout.session.completed"


def test_owner_triggers_payment_fulfillment(monkeypatch):
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token-test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    # Just test the endpoint accepts the request and has proper auth
    fulfill = client.post(
        "/owner/fulfill/paid-orders",
        headers={"Authorization": "Bearer owner-token-test"},
        json={},
    )

    assert fulfill.status_code == 200
    data = fulfill.json()
    assert data["status"] == "completed"
    assert "orders_processed" in data
    assert "results" in data


def test_webhook_replay_protection_rejects_duplicate_event(monkeypatch):
    """Verify that duplicate Stripe webhook events are rejected via idempotency_key."""
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_CHECKOUT_ENABLED", "true")

    # Use a unique event ID to avoid collisions with previous test runs
    import uuid
    unique_event_id = f"evt_replay_{uuid.uuid4().hex[:8]}"

    payload = {
        "id": unique_event_id,  # Unique event ID for idempotency testing
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_456",
                "metadata": {"order_id": "order_replay", "opportunity_id": "opp_replay"},
                "amount_total": 2500,
                "currency": "usd",
                "customer_details": {"email": "replay@example.com"},
            }
        },
    }
    raw = __import__("json").dumps(payload).encode()
    timestamp = "1700000000"
    signature = __import__("hmac").new(
        b"whsec_123",
        f"{timestamp}.{raw.decode('utf-8')}".encode("utf-8"),
        __import__("hashlib").sha256,
    ).hexdigest()

    # Send first event
    response1 = client.post(
        "/owner/checkout/webhook",
        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
        content=raw,
    )
    assert response1.status_code == 200
    assert response1.json()["status"] == "processed"

    # Send duplicate event with same ID
    response2 = client.post(
        "/owner/checkout/webhook",
        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
        content=raw,
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["status"] == "duplicate"
    assert data["event_id"] == unique_event_id
    assert "already been processed" in data["note"]
