"""Tests for AION FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from aion.main import app
from aion.schemas import AIResponse

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
