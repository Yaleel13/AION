"""YaliTek canonical knowledge loader gates."""

from aion.yalitek_knowledge import knowledge_approved, path_allowed_for_ingest, public_safe_summary


def test_not_approved_by_default(monkeypatch):
    monkeypatch.delenv("AION_YALITEK_KNOWLEDGE_APPROVED", raising=False)
    assert knowledge_approved() is False
    summary = public_safe_summary()
    assert summary["reliance"] == "draft_only_awaiting_owner_approval"
    assert summary["services"] == []
    assert summary["may_quote_unpublished_prices"] is False


def test_approved_exposes_services(monkeypatch):
    monkeypatch.setenv("AION_YALITEK_KNOWLEDGE_APPROVED", "true")
    summary = public_safe_summary()
    assert summary["approved"] is True
    assert "Website repair" in summary["services"]


def test_forbidden_ingest_paths():
    assert path_allowed_for_ingest("docs/services.md") is True
    assert path_allowed_for_ingest(".env") is False
    assert path_allowed_for_ingest("secrets/customers.csv") is False
    assert path_allowed_for_ingest("ops/wallet.json") is False
