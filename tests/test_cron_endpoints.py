"""Tests for AION Cron endpoints."""

from fastapi.testclient import TestClient
from api.cron.fulfillment import app

client = TestClient(app)


def test_cron_fulfillment_requires_cron_secret(monkeypatch):
    """Verify that cron endpoint requires CRON_SECRET."""
    monkeypatch.delenv("CRON_SECRET", raising=False)

    response = client.get(
        "/api/cron/fulfillment",
        headers={"Authorization": "Bearer anything"},
    )
    assert response.status_code == 503
    assert "CRON_SECRET is not configured" in response.json()["detail"]


def test_cron_fulfillment_rejects_invalid_token(monkeypatch):
    """Verify that cron endpoint rejects invalid bearer token."""
    monkeypatch.setenv("CRON_SECRET", "test-secret-123")

    response = client.get(
        "/api/cron/fulfillment",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_cron_fulfillment_disabled_by_default(monkeypatch):
    """Verify that fulfillment cron is disabled without FULFILLMENT_CRON_ENABLED flag."""
    monkeypatch.setenv("CRON_SECRET", "test-secret")
    monkeypatch.delenv("FULFILLMENT_CRON_ENABLED", raising=False)

    response = client.get(
        "/api/cron/fulfillment",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["scheduled"] is False
    assert "not set to true" in data["reason"]
    assert data["orders_processed"] == 0


def test_cron_fulfillment_skipped_when_kill_switch_engaged(monkeypatch, tmp_path):
    """Verify that fulfillment cron is skipped when kill switch is engaged."""
    monkeypatch.setenv("CRON_SECRET", "test-secret")
    monkeypatch.setenv("FULFILLMENT_CRON_ENABLED", "true")
    monkeypatch.setenv("AION_PHASE2_DB", str(tmp_path / "phase2.db"))
    monkeypatch.setenv("AION_KILL_SWITCH", "true")

    response = client.get(
        "/api/cron/fulfillment",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["scheduled"] is False
    assert "Kill switch engaged" in data["reason"]
    assert data["orders_processed"] == 0
