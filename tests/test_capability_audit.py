"""HTTP correlation and privacy using the real existing audit store schema."""
import asyncio
import json
import sys
from types import SimpleNamespace

import httpx
import pytest

from aion import capabilities, capability_audit, local_validation, phase2_services, runtime_status
from aion.main import app
from aion.moltbook.store import Phase2Store
from tests.test_local_validation import process_tree, wait_ready, assert_tree_stopped


@pytest.fixture(autouse=True)
def audit_attempts(monkeypatch):
    native_record = capability_audit.CapabilityAudit.record
    attempts = []

    def record(audit, event, **kwargs):
        attempts.append((audit, audit.request_id, event, audit.job_started, kwargs))
        return native_record(audit, event, **kwargs)

    monkeypatch.setattr(capability_audit.CapabilityAudit, "record", record)
    yield attempts
    requests = {id(item[0]) for item in attempts}
    ids = set()
    for request in requests:
        rows = [item for item in attempts if id(item[0]) == request]
        request_ids = {item[1] for item in rows}
        assert len(request_ids) == 1
        assert not ids.intersection(request_ids)
        ids.update(request_ids)
        assert sum(item[2] == "outcome" for item in rows) == 1
        assert rows[-1][2] == "outcome"
        assert sum(item[2] == "job_started" for item in rows) <= 1
        assert all(item[3] is True for item in rows if item[2] == "job_started")


@pytest.fixture
def audit_store(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "private-owner-credential")
    store = Phase2Store(str(tmp_path / "audit.db"))
    monkeypatch.setattr(phase2_services, "get_services", lambda: SimpleNamespace(store=store))
    yield store
    store._conn.close()


def events(store, request_id=None):
    rows = list(reversed(store.list_audit()))
    if request_id:
        rows = [row for row in rows if row["detail"]["request_id"] == request_id]
    for row in rows:
        assert row["module"] == "capabilities"
        assert set(row["detail"]) <= {
            "request_id", "capability", "permission", "path", "method",
            "policy_decision", "job_started", "outcome", "status_code",
        }
    serialized = json.dumps(rows)
    for secret in ["private-owner-credential", "private-policy-error", "private-output", "private-body"]:
        assert secret not in serialized
    return rows


async def call(path, **kwargs):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://test") as client:
        method = "POST" if path == "/local-executive/validate" else "GET"
        kwargs.setdefault("headers", {"Authorization": "Bearer private-owner-credential"})
        if method == "POST":
            kwargs.setdefault("json", {})
        return await client.request(method, path, **kwargs)


@pytest.mark.parametrize("path,capability", [
    ("/runtime/status", "runtime_status"), ("/owner/runtime/status", "runtime_status"),
    ("/local-executive/validate", "runtime.syntax"),
])
@pytest.mark.parametrize("failure", ["denied", "failure"])
async def test_http_policy_decision_and_outcome_without_process_start(path, capability, failure, audit_store, monkeypatch):
    catalog = capabilities.capability_catalog()
    catalog["capabilities"][capability]["configured"] = False

    def policy():
        if failure == "failure":
            raise RuntimeError("private-policy-error")
        return catalog

    async def forbidden(*args, **kwargs):
        pytest.fail("Denied request spawned a process")

    monkeypatch.setattr(capabilities, "capability_catalog", policy)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    response = await call(path)
    assert response.status_code == (403 if failure == "denied" else 503)
    rows = events(audit_store, response.headers["x-aion-request-id"])
    assert [row["action"] for row in rows] == ["capability.policy", "capability.outcome"]
    assert all(row["detail"]["capability"] == capability for row in rows)
    assert all(row["detail"]["job_started"] is False for row in rows)
    assert rows[-1]["detail"]["outcome"] == ("denied" if failure == "denied" else "policy_unavailable")


@pytest.mark.parametrize("path", ["/runtime/status", "/owner/runtime/status"])
async def test_status_http_success_correlates_without_copying_snapshot(path, audit_store, monkeypatch):
    snapshot = {"ok": True, "private-output": "private-owner-credential"}
    monkeypatch.setattr(runtime_status, "build_runtime_status", lambda: snapshot)
    response = await call(path, headers={"Authorization": "Bearer private-owner-credential", "x-aion-request-id": "private-body"})
    assert response.json() == snapshot
    rows = events(audit_store, response.headers["x-aion-request-id"])
    assert len(rows) == 2
    assert rows[0]["detail"]["policy_decision"] == "allowed"
    assert rows[-1]["detail"]["outcome"] == "succeeded"
    assert rows[-1]["detail"]["job_started"] is False
    assert response.headers["x-aion-request-id"] != "private-body"


async def test_syntax_success_records_actual_process_start_without_output(audit_store, monkeypatch):
    monkeypatch.setattr(local_validation, "ARGV", (sys.executable, "-I", "-c", "print('private-output')"))
    response = await call("/local-executive/validate")
    assert response.json()["status"] == "succeeded"
    assert response.json()["output"].strip() == "private-output"
    rows = events(audit_store, response.headers["x-aion-request-id"])
    assert [row["action"] for row in rows] == ["capability.policy", "capability.job_started", "capability.outcome"]
    assert rows[0]["detail"]["job_started"] is False
    assert rows[-1]["detail"]["job_started"] is True
    assert rows[-1]["detail"]["outcome"] == "succeeded"


@pytest.mark.parametrize("started", [False, True])
async def test_process_start_failure_is_distinct_from_a_failed_started_job(started, audit_store, monkeypatch):
    if started:
        monkeypatch.setattr(local_validation, "ARGV", (sys.executable, "-I", "-c", "raise SystemExit(1)"))
    else:
        async def unavailable(*args, **kwargs):
            raise OSError("private-output")
        monkeypatch.setattr(asyncio, "create_subprocess_exec", unavailable)
    response = await call("/local-executive/validate")
    assert response.status_code == 200
    rows = events(audit_store, response.headers["x-aion-request-id"])
    assert rows[0]["detail"]["policy_decision"] == "allowed"
    assert rows[-1]["detail"]["job_started"] is started
    assert rows[-1]["detail"]["outcome"] == ("failed" if started else "unavailable")
    assert any(row["action"] == "capability.job_started" for row in rows) is started


async def test_normal_service_facade_persists_correlated_http_events(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "private-owner-credential")
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AION_PHASE2_DB", str(tmp_path / "phase2.db"))
    monkeypatch.setenv("AION_PAPER_DB", str(tmp_path / "paper.db"))
    monkeypatch.setattr(runtime_status, "build_runtime_status", lambda: {"ok": True})
    phase2_services.reset_services_cache()
    try:
        status = await call("/owner/runtime/status")
        syntax = await call("/local-executive/validate")
        assert status.status_code == syntax.status_code == 200
        assert syntax.json()["status"] == "succeeded"
        store = phase2_services.get_services().store
        status_rows = events(store, status.headers["x-aion-request-id"])
        syntax_rows = events(store, syntax.headers["x-aion-request-id"])
        assert [row["action"] for row in status_rows] == ["capability.policy", "capability.outcome"]
        assert [row["action"] for row in syntax_rows] == ["capability.policy", "capability.job_started", "capability.outcome"]
        assert status_rows[-1]["detail"]["outcome"] == syntax_rows[-1]["detail"]["outcome"] == "succeeded"
    finally:
        phase2_services.reset_services_cache()


async def test_timeout_is_recorded_after_process_tree_cleanup(audit_store, process_tree, monkeypatch):
    monkeypatch.setattr(local_validation, "TIMEOUT_SECONDS", 2)
    response = await call("/local-executive/validate")
    assert response.json()["status"] == "timeout"
    rows = events(audit_store, response.headers["x-aion-request-id"])
    assert rows[-1]["detail"]["outcome"] == "timeout"
    assert rows[-1]["detail"]["job_started"] is True
    assert rows[-1]["success"] is False
    await assert_tree_stopped(process_tree)


@pytest.mark.parametrize("sink_failure", [False, True])
async def test_http_disconnect_during_startup_audits_after_cleanup(audit_store, process_tree, monkeypatch, sink_failure, audit_attempts):
    real_spawn = asyncio.create_subprocess_exec
    release = asyncio.Event()
    disconnected = asyncio.Event()

    async def slow_spawn(*args, **kwargs):
        child = await real_spawn(*args, **kwargs)
        await release.wait()
        return child

    body_sent = False

    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": b"{}", "more_body": False}
        if process_tree.exists():
            disconnected.set()
            return {"type": "http.disconnect"}
        await asyncio.sleep(100)

    sent = []

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0"}, "method": "POST",
             "scheme": "http", "path": "/local-executive/validate", "query_string": b"",
             "client": ("127.0.0.1", 123), "server": ("test", 80),
             "headers": [(b"authorization", b"Bearer private-owner-credential"), (b"content-type", b"application/json")]}
    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_spawn)
    if sink_failure:
        def unavailable(**kwargs):
            raise OSError("private-owner-credential")
        monkeypatch.setattr(audit_store, "append_audit", unavailable)
        monkeypatch.setattr(capability_audit.logger, "warning", unavailable)
    task = asyncio.create_task(app(scope, receive, send))
    try:
        await wait_ready(process_tree)
        await asyncio.wait_for(disconnected.wait(), 5)
        assert not task.done()
        assert [row["action"] for row in events(audit_store)] == ([] if sink_failure else ["capability.policy"])
        assert [item[2] for item in audit_attempts] == ["policy"]
    finally:
        release.set()
    await asyncio.wait_for(task, 5)
    assert sent[0]["status"] == 499
    assert [item[2] for item in audit_attempts] == ["policy", "job_started", "outcome"]
    assert audit_attempts[-1][4]["outcome"] == "cancelled"
    assert audit_attempts[-1][3] is True
    rows = events(audit_store)
    if not sink_failure:
        assert [row["action"] for row in rows] == ["capability.policy", "capability.job_started", "capability.outcome"]
        assert rows[-1]["detail"]["outcome"] == "cancelled"
        assert rows[-1]["detail"]["job_started"] is True
    await assert_tree_stopped(process_tree)


async def test_cancelled_http_request_records_outcome_after_cleanup(audit_store, process_tree):
    task = asyncio.create_task(call("/local-executive/validate"))
    try:
        await wait_ready(process_tree)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 5)
    rows = events(audit_store)
    assert rows[-1]["detail"]["outcome"] == "cancelled"
    assert rows[-1]["detail"]["job_started"] is True
    await assert_tree_stopped(process_tree)


async def test_concurrent_http_requests_have_distinct_correlation(audit_store, monkeypatch):
    monkeypatch.setattr(runtime_status, "build_runtime_status", lambda: {"ok": True})
    responses = await asyncio.gather(call("/runtime/status"), call("/owner/runtime/status"))
    ids = {response.headers["x-aion-request-id"] for response in responses}
    assert len(ids) == 2
    assert all(len(events(audit_store, request_id)) == 2 for request_id in ids)


@pytest.mark.parametrize("kwargs,status", [({"headers": {}}, 401), ({"json": {"command": "private-body"}}, 422)])
async def test_transport_rejection_is_not_a_policy_decision_or_job_start(kwargs, status, audit_store):
    response = await call("/local-executive/validate", **kwargs)
    assert response.status_code == status
    rows = events(audit_store, response.headers["x-aion-request-id"])
    assert len(rows) == 1
    assert rows[0]["detail"]["policy_decision"] == "not_evaluated"
    assert rows[0]["detail"]["job_started"] is False
    assert rows[0]["detail"]["outcome"] == "rejected"


async def test_unavailable_audit_sink_preserves_http_result(audit_store, monkeypatch, caplog):
    def unavailable(**kwargs):
        raise RuntimeError("private-owner-credential")

    monkeypatch.setattr(audit_store, "append_audit", unavailable)
    monkeypatch.setattr(runtime_status, "build_runtime_status", lambda: {"ok": True})
    response = await call("/owner/runtime/status")
    assert response.status_code == 200
    assert "Capability audit storage unavailable" in caplog.text
    assert "private-owner-credential" not in caplog.text


@pytest.mark.parametrize("outcome", ["succeeded", "timeout", "cancelled"])
@pytest.mark.parametrize("logging_failure", [False, True])
async def test_sink_failures_cannot_interrupt_process_ownership_or_cleanup(
    outcome, logging_failure, audit_store, process_tree, monkeypatch, audit_attempts, caplog,
):
    def unavailable(*args, **kwargs):
        raise OSError("private-owner-credential")

    monkeypatch.setattr(audit_store, "append_audit", unavailable)
    if logging_failure:
        monkeypatch.setattr(capability_audit.logger, "warning", unavailable)
    if outcome == "succeeded":
        monkeypatch.setattr(local_validation, "ARGV", (sys.executable, "-I", "-c", "print('private-output')"))
    if outcome == "timeout":
        monkeypatch.setattr(local_validation, "TIMEOUT_SECONDS", 2)
    if outcome == "cancelled":
        task = asyncio.create_task(call("/local-executive/validate"))
        try:
            await wait_ready(process_tree)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 5)
    else:
        response = await asyncio.wait_for(call("/local-executive/validate"), 5)
        assert response.status_code == 200
        assert response.json()["status"] == outcome
    assert [item[2] for item in audit_attempts] == ["policy", "job_started", "outcome"]
    assert audit_attempts[-1][4]["outcome"] == outcome
    assert audit_attempts[-1][3] is True
    if outcome != "succeeded":
        await assert_tree_stopped(process_tree)
    assert audit_store.list_audit() == []  # Best effort does not claim persistence.
    assert "private-owner-credential" not in caplog.text
    assert "private-output" not in caplog.text
