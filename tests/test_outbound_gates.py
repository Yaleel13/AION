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
