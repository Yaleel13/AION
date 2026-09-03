from __future__ import annotations

from aion.outbound_gates import build_outbound_gate_status


def test_gate_status_reports_go_live_checklist(monkeypatch) -> None:
    monkeypatch.setenv("AION_KILL_SWITCH", "false")
    monkeypatch.setenv("MOLTBOOK_MODE", "mock")
    monkeypatch.delenv("MOLTBOOK_API_KEY", raising=False)
    monkeypatch.delenv("MOLTBOOK_OUTBOUND_ENABLED", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("STRIPE_CHECKOUT_ENABLED", raising=False)
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    monkeypatch.delenv("FULFILLMENT_CRON_ENABLED", raising=False)

    status = build_outbound_gate_status()
    ids = {item["id"] for item in status["go_live_checklist"]}
    assert "postgres" in ids
    assert "stripe" in ids
    assert "outbound" in ids
    assert status["ready_for_live_outbound"] is False
    assert status["ready_for_revenue"] is False
    stripe = next(item for item in status["go_live_checklist"] if item["id"] == "stripe")
    assert stripe["ok"] is False


def test_gate_status_reports_execute_without_outbound(monkeypatch) -> None:
    monkeypatch.setenv("AION_KILL_SWITCH", "false")
    monkeypatch.setenv("MOLTBOOK_MODE", "live")
    monkeypatch.setenv("MOLTBOOK_API_KEY", "moltbook_test_key_placeholder")
    monkeypatch.setenv("MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1")
    monkeypatch.setenv("MOLTBOOK_EXECUTE_ENABLED", "true")
    monkeypatch.delenv("MOLTBOOK_OUTBOUND_ENABLED", raising=False)

    status = build_outbound_gate_status()
    assert status["moltbook_mode"] == "live"
    assert status["moltbook_api_key_set"] is True
    assert status["moltbook_outbound_enabled"] is False
    assert status["moltbook_execute_enabled"] is True
    assert "MOLTBOOK_OUTBOUND_ENABLED" in (status["moltbook_error"] or "")
    assert any("MOLTBOOK_OUTBOUND_ENABLED=true" in action for action in status["owner_actions"])
    live = next(item for item in status["go_live_checklist"] if item["id"] == "moltbook_live")
    outbound = next(item for item in status["go_live_checklist"] if item["id"] == "outbound")
    assert live["ok"] is True
    assert outbound["ok"] is False
