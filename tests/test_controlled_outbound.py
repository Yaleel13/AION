from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from aion.moltbook.approval import ApprovalDecision, OutboundAction, Phase2ApprovalGate
from aion.moltbook.controlled_outbound import approve_and_send_comment, controlled_outbound_status
from aion.moltbook.errors import MoltbookOutboundDisabledError
from aion.moltbook.security import KillSwitch
from aion.moltbook.settings import load_moltbook_settings
from aion.moltbook.store import Phase2Store


def _svc(tmp_path: Path):
    store = Phase2Store(str(tmp_path / "phase2.db"))
    kill = KillSwitch(engaged=False)
    gate = Phase2ApprovalGate(store, kill_switch=kill, token_pepper="test-pepper")
    return SimpleNamespace(store=store, kill_switch=kill, gate=gate)


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOLTBOOK_MODE", "live")
    monkeypatch.setenv("MOLTBOOK_API_KEY", "test-key")
    monkeypatch.setenv("MOLTBOOK_OUTBOUND_ENABLED", "true")
    monkeypatch.setenv("MOLTBOOK_PHASE2_EXECUTE", "true")


def test_controlled_outbound_requires_both_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOLTBOOK_MODE", "live")
    monkeypatch.setenv("MOLTBOOK_API_KEY", "test-key")
    monkeypatch.delenv("MOLTBOOK_OUTBOUND_ENABLED", raising=False)
    monkeypatch.delenv("MOLTBOOK_PHASE2_EXECUTE", raising=False)
    assert load_moltbook_settings().controlled_outbound_ready is False

    monkeypatch.setenv("MOLTBOOK_OUTBOUND_ENABLED", "true")
    assert load_moltbook_settings().controlled_outbound_ready is False

    monkeypatch.setenv("MOLTBOOK_PHASE2_EXECUTE", "true")
    settings = load_moltbook_settings()
    assert settings.controlled_outbound_ready is True
    assert settings.outbound_enabled is True
    assert settings.execute_enabled is True


@pytest.mark.asyncio
async def test_owner_approved_comment_uses_stored_payload_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable(monkeypatch)
    svc = _svc(tmp_path)
    req = svc.gate.propose(
        OutboundAction.COMMENT,
        summary="reply",
        payload={"post_id": "post-1", "content": "Exact approved text", "parent_id": None},
        idempotency_key="lead-1",
    )

    calls: list[dict] = []

    class Response:
        status_code = 201

    class Client:
        def __init__(self, **kwargs):
            del kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, headers, json):
            calls.append({"url": url, "headers": headers, "json": json})
            return Response()

    monkeypatch.setattr("aion.moltbook.controlled_outbound.httpx.AsyncClient", Client)
    result = await approve_and_send_comment(
        svc,
        request_id=req.request_id,
        expected_content_hash=req.content_hash,
    )
    assert result["published"] is True
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/posts/post-1/comments")
    assert calls[0]["json"] == {"content": "Exact approved text"}
    assert svc.gate.get(req.request_id).decision is ApprovalDecision.EXECUTED

    with pytest.raises(MoltbookOutboundDisabledError):
        await approve_and_send_comment(
            svc,
            request_id=req.request_id,
            expected_content_hash=req.content_hash,
        )
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_controlled_outbound_is_comment_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable(monkeypatch)
    svc = _svc(tmp_path)
    req = svc.gate.propose(
        OutboundAction.CREATE_POST,
        summary="post",
        payload={"submolt": "general", "title": "x", "content": "y"},
    )
    with pytest.raises(MoltbookOutboundDisabledError, match="Only comment"):
        await approve_and_send_comment(
            svc,
            request_id=req.request_id,
            expected_content_hash=req.content_hash,
        )


@pytest.mark.asyncio
async def test_controlled_send_quota_is_three_per_day(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable(monkeypatch)
    svc = _svc(tmp_path)

    class Response:
        status_code = 201

    class Client:
        def __init__(self, **kwargs):
            del kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, headers, json):
            del url, headers, json
            return Response()

    monkeypatch.setattr("aion.moltbook.controlled_outbound.httpx.AsyncClient", Client)

    requests = []
    for index in range(4):
        requests.append(svc.gate.propose(
            OutboundAction.COMMENT,
            summary=f"reply {index}",
            payload={"post_id": f"post-{index}", "content": f"text {index}", "parent_id": None},
            idempotency_key=f"lead-{index}",
        ))

    for req in requests[:3]:
        result = await approve_and_send_comment(svc, request_id=req.request_id, expected_content_hash=req.content_hash)
        assert result["published"] is True

    status = controlled_outbound_status(svc.gate)
    assert status["sent_last_24h"] == 3
    assert status["remaining_last_24h"] == 0

    with pytest.raises(MoltbookOutboundDisabledError, match="send quota"):
        await approve_and_send_comment(
            svc,
            request_id=requests[3].request_id,
            expected_content_hash=requests[3].content_hash,
        )
