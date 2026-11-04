from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import sys
from types import SimpleNamespace

import httpx
import pytest

from aion import capabilities, local_validation, main, phase2_services
from aion.moltbook.store import (
    RUNTIME_SYNTAX_CAPABILITY,
    Phase2Store,
    RuntimeSyntaxApprovalClaim,
)

AGENT = "agent-redemption-token"
PRINCIPAL = "agent:redemption-test"


@pytest.fixture
def redemption_store(tmp_path, monkeypatch):
    store = Phase2Store(str(tmp_path / "redemption.sqlite3"))
    services = SimpleNamespace(store=store)
    monkeypatch.setattr(main, "get_services", lambda: services)
    monkeypatch.setattr(phase2_services, "get_services", lambda: services)
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "owner-redemption-token")
    monkeypatch.setenv("AION_LOCAL_AGENT_TOKEN", AGENT)
    monkeypatch.setenv("AION_LOCAL_AGENT_PRINCIPAL", PRINCIPAL)
    return store


def approved(store: Phase2Store, *, principal: str = PRINCIPAL) -> str:
    execution_request_id = store.create_runtime_syntax_approval(
        requester_principal=principal,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    assert store.decide_runtime_syntax_approval(
        execution_request_id,
        approved=True,
        decided_by="owner",
    )
    return execution_request_id


async def redeem(
    execution_request_id: str,
    *,
    body: dict | None = None,
    client_host: str = "127.0.0.1",
    query: str = "",
) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app, client=(client_host, 123)),
        base_url="http://test",
    ) as client:
        return await client.post(
            f"/agent/runtime-syntax-approvals/{execution_request_id}/redeem{query}",
            headers={"Authorization": f"Bearer {AGENT}"},
            json={} if body is None else body,
        )


@pytest.fixture
def forbid_subprocess(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        pytest.fail("Denied redemption launched a subprocess")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)


async def test_approved_redemption_launches_once_and_audits_correlations(redemption_store, monkeypatch):
    native_spawn = asyncio.create_subprocess_exec
    launches = []

    async def counted_spawn(*args, **kwargs):
        launches.append((args, kwargs))
        return await native_spawn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", counted_spawn)
    monkeypatch.setattr(
        local_validation,
        "ARGV",
        (sys.executable, "-I", "-c", "print('private-validator-output')"),
    )
    execution_request_id = approved(redemption_store)
    response = await redeem(execution_request_id)

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert len(launches) == 1
    runtime_request_id = response.headers["x-aion-request-id"]
    rows = [
        row for row in redemption_store.list_audit()
        if row["detail"].get("request_id") == runtime_request_id
    ]
    assert [row["action"] for row in reversed(rows)] == [
        "capability.policy",
        "capability.job_started",
        "capability.outcome",
    ]
    assert all(row["detail"].get("approval_request_id") == execution_request_id for row in rows)
    serialized = str(rows)
    assert AGENT not in serialized
    assert "owner-redemption-token" not in serialized
    assert "private-validator-output" not in serialized
    assert redemption_store.get_runtime_syntax_approval(execution_request_id)["consumed_at"] is not None


@pytest.mark.parametrize("state", ["pending", "expired", "replayed", "wrong_principal"])
async def test_ineligible_redemptions_never_launch(redemption_store, forbid_subprocess, state):
    if state == "pending":
        execution_request_id = redemption_store.create_runtime_syntax_approval(
            requester_principal=PRINCIPAL,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
    elif state == "wrong_principal":
        execution_request_id = approved(redemption_store, principal="agent:other")
    else:
        execution_request_id = approved(redemption_store)
        if state == "expired":
            redemption_store._conn.execute(
                "UPDATE runtime_syntax_approvals SET expires_at = ? WHERE execution_request_id = ?",
                (datetime.now(timezone.utc).isoformat(), execution_request_id),
            )
            redemption_store._conn.commit()
        if state == "replayed":
            assert redemption_store.claim_runtime_syntax_approval(
                execution_request_id,
                capability=RUNTIME_SYNTAX_CAPABILITY,
                requester_principal=PRINCIPAL,
            ).claimed

    response = await redeem(execution_request_id)
    assert response.status_code == 403


async def test_denied_redemption_never_launches(redemption_store, forbid_subprocess):
    execution_request_id = redemption_store.create_runtime_syntax_approval(
        requester_principal=PRINCIPAL,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    assert redemption_store.decide_runtime_syntax_approval(
        execution_request_id,
        approved=False,
        decided_by="owner",
    )
    assert (await redeem(execution_request_id)).status_code == 403


async def test_policy_denial_and_storage_failure_never_spend_or_launch(
    redemption_store, forbid_subprocess, monkeypatch
):
    policy_denied = approved(redemption_store)
    original_catalog = capabilities.capability_catalog
    catalog = capabilities.capability_catalog()
    catalog["capabilities"]["runtime.syntax"]["execute"] = False
    monkeypatch.setattr(capabilities, "capability_catalog", lambda: catalog)
    assert (await redeem(policy_denied)).status_code == 403
    assert redemption_store.get_runtime_syntax_approval(policy_denied)["consumed_at"] is None

    monkeypatch.setattr(capabilities, "capability_catalog", original_catalog)
    unavailable = approved(redemption_store)
    monkeypatch.setattr(
        redemption_store,
        "claim_runtime_syntax_approval",
        lambda *_args, **_kwargs: RuntimeSyntaxApprovalClaim(
            claimed=False,
            reason="storage_unavailable",
        ),
    )
    assert (await redeem(unavailable)).status_code == 503
    assert redemption_store.get_runtime_syntax_approval(unavailable)["consumed_at"] is None


async def test_non_sqlite_storage_and_uncertain_commit_never_launch(
    redemption_store, forbid_subprocess, monkeypatch
):
    execution_request_id = approved(redemption_store)
    monkeypatch.setattr(redemption_store, "backend", "postgres")
    assert (await redeem(execution_request_id)).status_code == 503
    monkeypatch.setattr(redemption_store, "backend", "sqlite")

    original_connection = redemption_store._conn

    class CommitFailureConnection:
        def execute(self, *args, **kwargs):
            return original_connection.execute(*args, **kwargs)

        def commit(self):
            raise OSError("commit outcome unavailable")

        def rollback(self):
            return original_connection.rollback()

    original_authorize = capabilities.authorize_capability

    def arm_commit_failure(*args, **kwargs):
        handler = original_authorize(*args, **kwargs)
        redemption_store._conn = CommitFailureConnection()
        return handler

    monkeypatch.setattr(capabilities, "authorize_capability", arm_commit_failure)
    assert (await redeem(execution_request_id)).status_code == 503
    redemption_store._conn = original_connection
    assert redemption_store.get_runtime_syntax_approval(execution_request_id)["consumed_at"] is None


async def test_claim_stays_spent_when_launch_fails(redemption_store, monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise OSError("launch unavailable")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unavailable)
    execution_request_id = approved(redemption_store)
    response = await redeem(execution_request_id)

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert redemption_store.get_runtime_syntax_approval(execution_request_id)["consumed_at"] is not None


async def test_claim_stays_spent_when_redeeming_caller_disconnects(redemption_store, monkeypatch):
    started = asyncio.Event()

    async def waiting_validation():
        started.set()
        await asyncio.Event().wait()

    request = httpx.Request("POST", "http://test")
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 123),
        "headers": request.headers.raw,
        "query_string": b"",
    }
    http_request = main.Request(scope)

    async def disconnected():
        await started.wait()
        return True

    monkeypatch.setattr(local_validation, "run_validation", waiting_validation)
    monkeypatch.setattr(http_request, "is_disconnected", disconnected)
    execution_request_id = approved(redemption_store)
    with pytest.raises(main.HTTPException) as error:
        await main.redeem_runtime_syntax_approval(
            execution_request_id,
            main.RuntimeSyntaxApprovalRedemptionRequest(),
            http_request,
            f"Bearer {AGENT}",
        )

    assert error.value.status_code == 499
    assert redemption_store.get_runtime_syntax_approval(execution_request_id)["consumed_at"] is not None


async def test_redemption_accepts_only_the_server_issued_id(redemption_store, forbid_subprocess):
    execution_request_id = approved(redemption_store)
    assert (await redeem(
        execution_request_id,
        body={
            "capability": "runtime.syntax",
            "requester_principal": PRINCIPAL,
            "execution_parameters": ["caller-selected"],
            "audit_id": "caller-selected",
        },
    )).status_code == 422
    assert (await redeem("x" * 32)).status_code == 400
    assert (await redeem(execution_request_id, query="?audit_id=caller-selected")).status_code == 400


async def test_concurrent_redemption_uses_two_sqlite_connections_and_launches_once(
    redemption_store, monkeypatch
):
    execution_request_id = approved(redemption_store)
    second_store = Phase2Store(redemption_store.path)
    services = iter(
        [
            SimpleNamespace(store=redemption_store),
            SimpleNamespace(store=second_store),
        ]
    )
    monkeypatch.setattr(main, "get_services", lambda: next(services))
    native_spawn = asyncio.create_subprocess_exec
    launches = []

    async def counted_spawn(*args, **kwargs):
        launches.append((args, kwargs))
        return await native_spawn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", counted_spawn)
    first, second = await asyncio.gather(
        redeem(execution_request_id),
        redeem(execution_request_id),
    )

    assert sorted((first.status_code, second.status_code)) == [200, 403]
    assert len(launches) == 1
