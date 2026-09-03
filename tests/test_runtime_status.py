"""Contract tests for GET /runtime/status."""

from __future__ import annotations

from fastapi.testclient import TestClient

from aion.main import app

client = TestClient(app)


def test_runtime_status_shape_and_safe_defaults():
    response = client.get("/runtime/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["fixture"] is False
    assert data["source"] == "runtime_status"

    assert "backend" in data["storage"]
    assert data["storage"]["configured"] is True

    assert data["moltbook"]["mode"] in {"mock", "live", None}
    assert data["moltbook"]["outbound_enabled"] is False
    assert data["moltbook"]["execute_enabled"] is False

    assert data["autonomy"]["mode"] == "inactive"
    assert data["autonomy"]["dry_run"] is True
    assert data["autonomy"]["live_writes_enabled"] is False
    assert data["autonomy"]["default"] == "inactive"

    assert data["kill_switch"]["engaged"] is False
    assert data["paper_market_data"]["live_trading"] is False
    assert "openai_configured" in data["providers"]
    assert "gemini_configured" in data["providers"]
    assert data["safety"]["paper_is_not_live_trading"] is True
    assert data["payment_rails"]["payment_orders_ledger"] is True


def test_runtime_status_ledger_is_independent_of_stripe_configuration(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("STRIPE_CHECKOUT_ENABLED", raising=False)

    data = client.get("/runtime/status").json()

    assert data["payment_rails"]["stripe_ready_for_checkout"] is False
    assert data["payment_rails"]["payment_orders_ledger"] is True


def test_runtime_status_respects_dry_run_env(monkeypatch):
    monkeypatch.setenv("MOLTBOOK_AUTONOMY_DRY_RUN", "false")
    # Autonomy still inactive by default — dry_run flag flips but live writes stay off.
    data = client.get("/runtime/status").json()
    assert data["autonomy"]["dry_run"] is False
    assert data["autonomy"]["mode"] == "inactive"
    assert data["autonomy"]["live_writes_enabled"] is False


def test_runtime_status_storage_sqlite_when_unset(monkeypatch):
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    data = client.get("/runtime/status").json()
    assert data["storage"]["backend"] == "sqlite"
    assert data["storage"]["configured"] is True


def test_runtime_status_preserves_flags_when_execute_lacks_outbound(monkeypatch):
    monkeypatch.setenv("MOLTBOOK_MODE", "live")
    monkeypatch.setenv("MOLTBOOK_API_KEY", "moltbook_test_key_placeholder")
    monkeypatch.setenv("MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1")
    monkeypatch.setenv("MOLTBOOK_EXECUTE_ENABLED", "true")
    monkeypatch.delenv("MOLTBOOK_OUTBOUND_ENABLED", raising=False)

    data = client.get("/runtime/status").json()
    moltbook = data["moltbook"]
    assert moltbook["configured"] is False
    assert moltbook["mode"] == "live"
    assert moltbook["api_key_present"] is True
    assert moltbook["outbound_enabled"] is False
    assert moltbook["execute_enabled"] is True
    assert moltbook["controlled_outbound_ready"] is False
    assert "MOLTBOOK_OUTBOUND_ENABLED" in moltbook["error"]
