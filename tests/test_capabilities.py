from __future__ import annotations

from aion.capabilities import capability_catalog, capability_registry


def test_capability_registry_has_no_global_unrestricted_autonomy(monkeypatch) -> None:
    monkeypatch.delenv("MOLTBOOK_OUTBOUND_ENABLED", raising=False)
    monkeypatch.delenv("MOLTBOOK_EXECUTE_ENABLED", raising=False)
    data = capability_registry()
    assert data["ok"] is True
    assert data["global_autonomy_switch"] is False
    assert data["capabilities"]["github_runtime"]["execute"] is False
    assert data["capabilities"]["notifications"]["execute"] is False
    assert data["capabilities"]["paper_market"]["scope"].startswith("Virtual BTC/ETH")


def test_moltbook_execute_defaults_closed(monkeypatch) -> None:
    monkeypatch.setenv("MOLTBOOK_MODE", "mock")
    monkeypatch.delenv("MOLTBOOK_OUTBOUND_ENABLED", raising=False)
    monkeypatch.delenv("MOLTBOOK_EXECUTE_ENABLED", raising=False)
    data = capability_registry()
    assert data["capabilities"]["moltbook"]["approve"] is False
    assert data["capabilities"]["moltbook"]["execute"] is False


def test_github_runtime_ignores_actions_runner_token(monkeypatch) -> None:
    monkeypatch.delenv("AION_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_APP_INSTALLATION_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "gh_actions_runner_token")
    data = capability_registry()
    assert data["capabilities"]["github_runtime"]["configured"] is False


def test_capability_catalog_is_env_independent(monkeypatch) -> None:
    monkeypatch.delenv("AION_OWNER_TOKEN", raising=False)
    monkeypatch.delenv("AION_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_APP_INSTALLATION_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "gh_actions_runner_token")
    catalog = capability_catalog()
    assert catalog["capabilities"]["moltbook"]["propose"] is True
    assert catalog["capabilities"]["github_runtime"]["configured"] is False
    live = capability_registry()
    assert live["capabilities"]["moltbook"]["propose"] is False
