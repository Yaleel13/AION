"""Tests for the Phase 1 read-only Moltbook integration."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from aion.moltbook.approval import OutboundAction, OutboundApprovalGate
from aion.moltbook.client import MoltbookClient, create_client, register_agent
from aion.moltbook.errors import (
    MoltbookConfigError,
    MoltbookOutboundDisabledError,
    MoltbookRateLimitError,
)
from aion.moltbook.redact import REDACTED, redact_text, redact_value
from aion.moltbook.settings import load_moltbook_settings, observe_moltbook_env


def test_settings_repr_hides_api_key() -> None:
    settings = load_moltbook_settings(
        environ={
            "MOLTBOOK_MODE": "live",
            "MOLTBOOK_API_KEY": "moltbook_sk_should_never_appear_in_repr",
            "MOLTBOOK_BASE_URL": "https://www.moltbook.com/api/v1",
        }
    )
    rendered = repr(settings)
    assert "moltbook_sk_should_never_appear_in_repr" not in rendered
    assert "api_key=<set>" in rendered


def test_gitignore_covers_private_env_files() -> None:
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in (".env", ".env.local", ".env.live"):
        result = subprocess.run(
            ["git", "check-ignore", "-v", name],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{name} must be gitignored"
        assert name in result.stdout or ".env" in result.stdout


def test_settings_default_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOLTBOOK_MODE", raising=False)
    monkeypatch.delenv("MOLTBOOK_API_KEY", raising=False)
    settings = load_moltbook_settings(environ={})
    assert settings.mode == "mock"
    assert settings.outbound_enabled is False
    assert settings.is_mock is True


def test_settings_live_requires_key() -> None:
    with pytest.raises(MoltbookConfigError, match="MOLTBOOK_API_KEY"):
        load_moltbook_settings(
            environ={
                "MOLTBOOK_MODE": "live",
                "MOLTBOOK_BASE_URL": "https://www.moltbook.com/api/v1",
            }
        )


def test_settings_rejects_non_www_live_host() -> None:
    with pytest.raises(MoltbookConfigError, match="www.moltbook.com"):
        load_moltbook_settings(
            environ={
                "MOLTBOOK_MODE": "live",
                "MOLTBOOK_API_KEY": "moltbook_test_key_placeholder",
                "MOLTBOOK_BASE_URL": "https://moltbook.com/api/v1",
            }
        )


def test_settings_rejects_outbound_flag() -> None:
    with pytest.raises(MoltbookConfigError, match="OUTBOUND"):
        load_moltbook_settings(
            environ={
                "MOLTBOOK_MODE": "mock",
                "MOLTBOOK_OUTBOUND_ENABLED": "true",
            }
        )


def test_settings_rejects_execute_without_outbound() -> None:
    with pytest.raises(MoltbookConfigError, match="MOLTBOOK_EXECUTE_ENABLED requires MOLTBOOK_OUTBOUND_ENABLED"):
        load_moltbook_settings(
            environ={
                "MOLTBOOK_MODE": "live",
                "MOLTBOOK_API_KEY": "moltbook_test_key_placeholder",
                "MOLTBOOK_BASE_URL": "https://www.moltbook.com/api/v1",
                "MOLTBOOK_EXECUTE_ENABLED": "true",
            }
        )


def test_observe_moltbook_env_reports_execute_without_outbound() -> None:
    observed = observe_moltbook_env(
        environ={
            "MOLTBOOK_MODE": "live",
            "MOLTBOOK_API_KEY": "moltbook_test_key_placeholder",
            "MOLTBOOK_EXECUTE_ENABLED": "true",
        }
    )
    assert observed.mode == "live"
    assert observed.api_key_present is True
    assert observed.outbound_enabled is False
    assert observed.execute_enabled is True


def test_redaction_strips_secrets_and_email() -> None:
    text = (
        "Authorization: Bearer moltbook_sk_abc123456789 "
        "contact me at owner@example.com"
    )
    redacted = redact_text(text)
    assert "moltbook_sk_abc123456789" not in redacted
    assert "owner@example.com" not in redacted
    assert REDACTED in redacted

    payload = redact_value(
        {"api_key": "secret", "nested": {"email": "a@b.co"}, "ok": "hello"}
    )
    assert payload["api_key"] == REDACTED
    assert payload["nested"]["email"] == REDACTED
    assert payload["ok"] == "hello"


@pytest.mark.asyncio
async def test_mock_read_operations() -> None:
    client = create_client(
        load_moltbook_settings(environ={"MOLTBOOK_MODE": "mock"})
    )
    profile = await client.profile()
    status = await client.status()
    feed = await client.feed(sort="hot", limit=5)
    post = await client.get_post("mock-post-1")
    comments = await client.get_comments("mock-post-1")
    search = await client.search("memory architecture")
    submolts = await client.list_submolts()
    submolt = await client.get_submolt("general")

    assert profile["untrusted"] is True
    assert status["status"] == "claimed"
    assert feed["mode"] == "mock"
    assert post["post"]["id"] == "mock-post-1"
    assert comments["comments"]
    assert search["query"] == "memory architecture"
    assert submolts["submolts"]
    assert submolt["submolt"]["name"] == "general"


@pytest.mark.asyncio
async def test_outbound_methods_are_blocked() -> None:
    client = create_client(
        load_moltbook_settings(environ={"MOLTBOOK_MODE": "mock"})
    )
    with pytest.raises(MoltbookOutboundDisabledError):
        await client.create_post(
            submolt="introductions", title="x", content="y"
        )
    with pytest.raises(MoltbookOutboundDisabledError):
        await client.comment(post_id="1", content="hi")
    with pytest.raises(MoltbookOutboundDisabledError):
        await client.follow("someone")
    with pytest.raises(MoltbookOutboundDisabledError):
        await client.subscribe("general")
    with pytest.raises(MoltbookOutboundDisabledError):
        await register_agent(name="AION", description="test")

    pending = client.approval_gate.list_pending()
    assert len(pending) >= 4
    assert all(p.action in OutboundAction for p in pending)


@pytest.mark.asyncio
async def test_live_client_retries_and_reads() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.headers.get("Authorization", "").startswith("Bearer ")
        if calls["n"] == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return httpx.Response(
            200,
            json={"status": "claimed", "agent": {"name": "AION"}},
        )

    transport = httpx.MockTransport(handler)
    settings = load_moltbook_settings(
        environ={
            "MOLTBOOK_MODE": "live",
            "MOLTBOOK_API_KEY": "moltbook_test_key_placeholder",
            "MOLTBOOK_BASE_URL": "https://www.moltbook.com/api/v1",
            "MOLTBOOK_MAX_RETRIES": "2",
        }
    )
    client = MoltbookClient(settings, transport=transport)
    result = await client.status()
    assert result["status"] == "claimed"
    assert result["untrusted"] is True
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_live_rate_limit_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "1"},
            json={"message": "Rate limit exceeded"},
        )

    settings = load_moltbook_settings(
        environ={
            "MOLTBOOK_MODE": "live",
            "MOLTBOOK_API_KEY": "moltbook_test_key_placeholder",
            "MOLTBOOK_BASE_URL": "https://www.moltbook.com/api/v1",
            "MOLTBOOK_MAX_RETRIES": "0",
        }
    )
    client = MoltbookClient(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(MoltbookRateLimitError):
        await client.profile()


@pytest.mark.asyncio
async def test_local_rate_limiter_blocks() -> None:
    settings = load_moltbook_settings(
        environ={
            "MOLTBOOK_MODE": "live",
            "MOLTBOOK_API_KEY": "moltbook_test_key_placeholder",
            "MOLTBOOK_RATE_LIMIT_PER_MINUTE": "1",
            "MOLTBOOK_MAX_RETRIES": "0",
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = MoltbookClient(settings, transport=httpx.MockTransport(handler))
    await client.profile()
    with pytest.raises(MoltbookRateLimitError, match="Local"):
        await client.profile()


@pytest.mark.asyncio
async def test_audit_log_redacts_and_writes(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    settings = load_moltbook_settings(
        environ={
            "MOLTBOOK_MODE": "mock",
            "MOLTBOOK_AUDIT_LOG_PATH": str(path),
        }
    )
    client = create_client(settings)
    await client.profile()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["action"] == "profile"
    assert event["success"] is True
    dumped = json.dumps(event)
    assert "moltbook_sk_" not in dumped
    assert "Bearer " not in dumped


def test_approval_gate_cannot_execute() -> None:
    gate = OutboundApprovalGate()
    req = gate.propose(
        OutboundAction.CREATE_POST,
        summary="test",
        payload={"title": "hi"},
    )
    gate.decide(req.request_id, approved=True, decided_by="owner")
    with pytest.raises(MoltbookOutboundDisabledError):
        gate.assert_executable(req)


def test_health_includes_moltbook() -> None:
    from fastapi.testclient import TestClient

    from aion.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["moltbook"]["phase"] == "phase2-controlled-growth"
    assert data["moltbook"]["outbound_enabled"] is False
    assert data["moltbook"]["outbound_enabled"] is False
