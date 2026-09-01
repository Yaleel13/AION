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
