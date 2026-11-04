from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from aion import main
from aion.moltbook.store import Phase2Store

OWNER = "owner-test-token"
AGENT = "agent-test-token"
PRINCIPAL = "agent:isolated-test"


@pytest.fixture
def approval_store(tmp_path, monkeypatch):
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))
    monkeypatch.setattr(main, "get_services", lambda: SimpleNamespace(store=store))
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", OWNER)
    monkeypatch.setenv("AION_LOCAL_AGENT_TOKEN", AGENT)
    monkeypatch.setenv("AION_LOCAL_AGENT_PRINCIPAL", PRINCIPAL)
    return store


@pytest.fixture
def forbid_subprocess(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        pytest.fail("Approval request or decision launched a subprocess")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)


async def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict | None = None,
    client_host: str = "127.0.0.1",
):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app, client=(client_host, 123)),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, headers=headers, json=body)


async def submit() -> str:
    response = await request("POST", "/agent/runtime-syntax-approvals", token=AGENT, body={})
    assert response.status_code == 200
    return response.json()["execution_request_id"]


async def test_agent_submission_is_fixed_and_rejects_anonymous_or_owner(
    approval_store, forbid_subprocess
):
    assert (await request("POST", "/agent/runtime-syntax-approvals", body={})).status_code == 401
    assert (await request("POST", "/agent/runtime-syntax-approvals", token=OWNER, body={})).status_code == 403
    assert (await request(
        "POST",
        "/agent/runtime-syntax-approvals",
        token=AGENT,
        body={
            "requester_principal": "caller-selected",
            "capability": "runtime.syntax",
            "executable": "caller-selected",
            "arguments": ["caller-selected"],
        },
    )).status_code == 422

    execution_request_id = await submit()
    row = approval_store.get_runtime_syntax_approval(execution_request_id)
    assert row and row["capability"] == "runtime.syntax"
    assert row["requester_principal"] == PRINCIPAL
    assert row["decision"] == "pending"


async def test_agent_identity_is_local_opt_in_and_same_token_fails_closed(
    approval_store, forbid_subprocess, monkeypatch
):
    monkeypatch.delenv("AION_LOCAL_AGENT_TOKEN")
    assert (await request("POST", "/agent/runtime-syntax-approvals", token=AGENT, body={})).status_code == 503

    monkeypatch.setenv("AION_LOCAL_AGENT_TOKEN", AGENT)
    monkeypatch.setenv("AION_RUNTIME_MODE", "cloud")
    assert (await request("POST", "/agent/runtime-syntax-approvals", token=AGENT, body={})).status_code == 503

    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    assert (await request(
        "POST",
        "/agent/runtime-syntax-approvals",
        token=AGENT,
        body={},
        client_host="192.0.2.1",
    )).status_code == 403

    execution_request_id = approval_store.create_runtime_syntax_approval(
        requester_principal=PRINCIPAL,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    monkeypatch.setenv("AION_LOCAL_AGENT_TOKEN", OWNER)
    assert (await request("POST", "/agent/runtime-syntax-approvals", token=OWNER, body={})).status_code == 403
    assert (await request(
        "POST",
        f"/owner/runtime-syntax-approvals/{execution_request_id}/decision",
        token=OWNER,
        body={"approved": True},
    )).status_code == 403


async def test_owner_review_decision_rejects_agent_and_repeated_decisions(
    approval_store, forbid_subprocess
):
    execution_request_id = await submit()
    path = f"/owner/runtime-syntax-approvals/{execution_request_id}"
    assert (await request("GET", path, token=AGENT)).status_code == 403
    assert (await request("POST", f"{path}/decision", token=AGENT, body={"approved": True})).status_code == 403

    review = await request("GET", path, token=OWNER)
    assert review.status_code == 200
    assert review.json()["execution_request_id"] == execution_request_id
    approved = await request("POST", f"{path}/decision", token=OWNER, body={"approved": True})
    assert approved.status_code == 200
    assert approved.json()["decision"] == "approved"
    assert (await request("POST", f"{path}/decision", token=OWNER, body={"approved": False})).status_code == 409


async def test_expired_request_and_invalid_owner_inputs_never_launch(
    approval_store, forbid_subprocess
):
    execution_request_id = approval_store.create_runtime_syntax_approval(
        requester_principal=PRINCIPAL,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    path = f"/owner/runtime-syntax-approvals/{execution_request_id}/decision"
    assert (await request("POST", path, token=OWNER, body={"approved": True})).status_code == 409
    assert (await request(
        "POST",
        "/owner/runtime-syntax-approvals/" + "x" * 32 + "/decision",
        token=OWNER,
        body={"approved": True},
    )).status_code == 400
    assert (await request(
        "POST",
        path,
        token=OWNER,
        body={"approved": True, "capability": "runtime.syntax"},
    )).status_code == 422
