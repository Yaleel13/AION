from __future__ import annotations

import asyncio
import ast
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

from aion import capabilities, local_tests, local_validation, main, phase2_services
from aion.main import app
from aion.moltbook.store import Phase2Store

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="POSIX process-group cleanup uses Linux /proc evidence")


@pytest.fixture(autouse=True)
def local_owner(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")


async def call(path="/local-executive/tests", *, body=None, host="127.0.0.1", token="test-owner"):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(host, 123)),
        base_url="http://test",
    ) as client:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return await client.post(path, json={} if body is None else body, headers=headers)


def process_running(pid: int) -> bool:
    stat = Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().split(") ", 1)[1].split()[0] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False


@pytest.fixture
def process_tree(tmp_path, monkeypatch):
    ready = tmp_path / "pids"
    script = tmp_path / "tree.py"
    script.write_text(
        "import os, signal, subprocess, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(120)'])\n"
        f"open({str(ready)!r}, 'w').write(str(os.getpid())+' '+str(child.pid))\n"
        "time.sleep(120)\n"
    )
    monkeypatch.setattr(local_tests, "ARGV", (sys.executable, "-I", str(script)))
    return ready


async def wait_ready(path: Path) -> None:
    while not path.exists() or len(path.read_text().split()) != 2:
        await asyncio.sleep(0.01)


async def assert_tree_stopped(path: Path) -> None:
    pids = [int(pid) for pid in path.read_text().split()]
    for _ in range(100):
        if all(not process_running(pid) for pid in pids):
            return
        await asyncio.sleep(0.01)
    pytest.fail("Runtime test process tree still running")


@pytest.mark.parametrize(
    ("token", "host", "body", "status"),
    [
        (None, "127.0.0.1", {}, 401),
        ("wrong", "127.0.0.1", {}, 403),
        ("test-owner", "192.0.2.1", {}, 403),
        ("test-owner", "127.0.0.1", {"argv": ["unsafe"]}, 422),
    ],
)
async def test_transport_denial_never_starts_runtime_tests(monkeypatch, token, host, body, status):
    async def forbidden(*_args, **_kwargs):
        pytest.fail("Denied runtime tests launched a process")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    response = await call(token=token, host=host, body=body)
    assert response.status_code == status


async def test_policy_denial_never_starts_runtime_tests(monkeypatch):
    catalog = capabilities.capability_catalog()
    catalog["capabilities"]["runtime.tests"]["execute"] = False

    async def forbidden(*_args, **_kwargs):
        pytest.fail("Policy-denied runtime tests launched a process")

    monkeypatch.setattr(capabilities, "capability_catalog", lambda: catalog)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    assert (await call()).status_code == 403


async def test_runtime_tests_succeed_without_exposing_output(monkeypatch):
    monkeypatch.setattr(
        local_tests,
        "ARGV",
        (sys.executable, "-I", "-c", "print('private-runtime-test-output')"),
    )
    response = await call()
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "ok": True,
        "job": "runtime.tests",
        "status": "succeeded",
        "duration_ms": data["duration_ms"],
    }
    assert isinstance(data["duration_ms"], int)
    assert data["duration_ms"] >= 0
    assert "private-runtime-test-output" not in response.text


async def test_runtime_test_failure_and_output_bound_stay_private(monkeypatch):
    monkeypatch.setattr(
        local_tests,
        "ARGV",
        (sys.executable, "-I", "-c", "import os; os.write(1, b'x' * 200000); raise SystemExit(1)"),
    )
    response = await call()
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "x" * 100 not in response.text

    result = await local_validation.run_fixed_job(
        argv=(sys.executable, "-I", "-c", "import os; os.write(1, b'x' * 200000)"),
        timeout_seconds=5,
        environment={"LANG": "C.UTF-8"},
        job="test.output-bound",
        include_output=True,
    )
    assert len(result["output"].encode()) <= local_validation.MAX_OUTPUT_BYTES
    assert result["truncated"] is True


async def test_timeout_and_cancellation_reap_runtime_test_process_group(process_tree, monkeypatch):
    monkeypatch.setattr(local_tests, "TIMEOUT_SECONDS", 1)
    timeout = await local_tests.run_runtime_tests()
    assert timeout["status"] == "timeout"
    await assert_tree_stopped(process_tree)
    process_tree.unlink()

    task = asyncio.create_task(local_tests.run_runtime_tests())
    try:
        await asyncio.wait_for(wait_ready(process_tree), 5)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 5)
    await assert_tree_stopped(process_tree)


async def test_runtime_tests_audit_correlation_excludes_output(tmp_path, monkeypatch):
    store = Phase2Store(str(tmp_path / "audit.db"))
    services = SimpleNamespace(store=store)
    monkeypatch.setattr(main, "get_services", lambda: services)
    monkeypatch.setattr(phase2_services, "get_services", lambda: services)
    monkeypatch.setattr(
        local_tests,
        "ARGV",
        (sys.executable, "-I", "-c", "print('private-runtime-test-output')"),
    )
    try:
        response = await call()
        request_id = response.headers["x-aion-request-id"]
        rows = list(reversed(store.list_audit(request_id=request_id)))
        assert [row["action"] for row in rows] == [
            "capability.policy",
            "capability.job_started",
            "capability.outcome",
        ]
        assert all(row["detail"]["capability"] == "runtime.tests" for row in rows)
        assert "private-runtime-test-output" not in str(rows)
    finally:
        store.close()


def test_manifest_is_fixed_and_matches_its_runner():
    module = ast.parse(
        (local_tests.PROJECT_ROOT / "scripts/validate_runtime_tests.py").read_text()
    )
    manifest = next(
        tuple(element.value for element in node.value.elts)
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "MANIFEST"
            for target in node.targets
        )
        and isinstance(node.value, ast.Tuple)
    )
    assert local_tests.MANIFEST == manifest
