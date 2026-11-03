from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import httpx
import pytest

from aion import local_validation as validation
from aion.main import app

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="POSIX process-group cleanup uses Linux /proc evidence")


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")
    monkeypatch.setenv("AION_OWNER_TOKEN", "test-owner")


@pytest.fixture(autouse=True)
def endpoint_tasks_are_drained(monkeypatch):
    native_create_task = asyncio.create_task
    tasks = []

    def create_task(coro, *args, **kwargs):
        task = native_create_task(coro, *args, **kwargs)
        if coro.__qualname__.endswith("watch_disconnect") or coro.__qualname__ == "dispatch_capability_async":
            tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", create_task)
    yield tasks
    assert all(task.done() for task in tasks), "Endpoint left a watcher or validation task pending"


@pytest.fixture(params=["executor", "dispatcher"])
def run_job(request):
    if request.param == "executor":
        return validation.run_validation
    from aion.capabilities import dispatch_capability_async
    return lambda: dispatch_capability_async("runtime.syntax", action="execute")


async def test_fixed_job_success_and_environment(monkeypatch):
    actual_spawn = asyncio.create_subprocess_exec
    captured = {}

    async def spawn(*args, **kwargs):
        captured.update(argv=args, **kwargs)
        return await actual_spawn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    result = await validation.run_validation()
    assert result["ok"] is True
    assert result["status"] == "succeeded"
    assert "Runtime syntax valid:" in result["output"]
    assert result["arbitrary_commands_enabled"] is False
    assert captured["argv"] == validation.ARGV
    assert captured["cwd"] == validation.PROJECT_ROOT
    assert captured["env"] == validation.JOB_ENV
    assert "AION_OWNER_TOKEN" not in captured["env"]
    assert captured["start_new_session"] is True


def process_running(pid):
    stat = Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().split(") ", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


@pytest.fixture
def process_tree(tmp_path, monkeypatch):
    ready = tmp_path / "pids"
    script = tmp_path / "tree.py"
    # Both processes ignore SIGTERM to ensure cleanup does not rely on cooperation.
    script.write_text(
        "import os, signal, subprocess, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(120)'])\n"
        f"open({str(ready)!r}, 'w').write(str(os.getpid())+' '+str(child.pid))\n"
        "time.sleep(120)\n"
    )
    monkeypatch.setattr(validation, "ARGV", (sys.executable, "-I", str(script)))
    return ready


async def wait_ready(path):
    async def poll():
        while not path.exists() or len(path.read_text().split()) != 2:
            await asyncio.sleep(0.01)
    await asyncio.wait_for(poll(), 5)


async def assert_tree_stopped(path):
    pids = [int(pid) for pid in path.read_text().split()]
    for _ in range(100):
        if all(not process_running(pid) for pid in pids):
            return
        await asyncio.sleep(0.01)
    pytest.fail("Validation process tree still running")


async def test_timeout_cleans_process_tree(process_tree, monkeypatch, run_job):
    monkeypatch.setattr(validation, "TIMEOUT_SECONDS", 2)
    result = await asyncio.wait_for(run_job(), 5)
    assert result["status"] == "timeout"
    assert result["ok"] is False
    await assert_tree_stopped(process_tree)


async def test_cancellation_cleans_process_tree(process_tree, run_job):
    task = asyncio.create_task(run_job())
    try:
        await wait_ready(process_tree)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 5)
    await assert_tree_stopped(process_tree)


async def test_cancellation_during_spawn_cleans_tree(process_tree, monkeypatch, run_job):
    real_spawn = asyncio.create_subprocess_exec
    release = asyncio.Event()

    async def slow_spawn(*args, **kwargs):
        process = await real_spawn(*args, **kwargs)
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_spawn)
    task = asyncio.create_task(run_job())
    try:
        await wait_ready(process_tree)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()  # Cleanup must survive repeated cancellation.
    finally:
        release.set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 5)
    await assert_tree_stopped(process_tree)


async def test_timeout_during_startup_cleans_tree(process_tree, monkeypatch, run_job):
    real_spawn = asyncio.create_subprocess_exec
    release = asyncio.Event()

    async def slow_spawn(*args, **kwargs):
        process = await real_spawn(*args, **kwargs)
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_spawn)
    monkeypatch.setattr(validation, "TIMEOUT_SECONDS", 0.05)
    task = asyncio.create_task(run_job())
    try:
        await wait_ready(process_tree)
        await asyncio.sleep(0.1)
        assert task.cancelling() > 0  # Deadline reached while still in startup.
        assert not task.done()  # It still owns the pending spawn/cleanup.
    finally:
        release.set()
    result = await asyncio.wait_for(task, 5)
    assert result["status"] == "timeout"
    await assert_tree_stopped(process_tree)


async def test_child_does_not_inherit_owner_token(monkeypatch, run_job):
    monkeypatch.setattr(validation, "ARGV", (sys.executable, "-I", "-c",
        "import os; assert 'AION_OWNER_TOKEN' not in os.environ; print('environment isolated')"))
    result = await run_job()
    assert result["ok"] is True
    assert result["output"].strip() == "environment isolated"


async def test_invalid_utf8_output_stays_bounded(monkeypatch, run_job):
    monkeypatch.setattr(validation, "ARGV", (sys.executable, "-I", "-c",
        "import os; os.write(1,b'\\xff'*24000)"))
    result = await run_job()
    assert result["ok"] is True
    assert len(result["output"].encode("utf-8")) <= validation.MAX_OUTPUT_BYTES
    assert result["truncated"] is True


async def test_output_is_bounded_and_drained(monkeypatch, run_job):
    monkeypatch.setattr(validation, "ARGV", (sys.executable, "-I", "-c",
        "import os; os.write(1,b'x'*200000); os.write(2,b'y'*200000)"))
    result = await asyncio.wait_for(run_job(), 5)
    assert result["ok"] is True
    assert len(result["output"].encode()) <= validation.MAX_OUTPUT_BYTES
    assert result["truncated"] is True


@pytest.mark.parametrize("host,token,mode,body,status", [
    ("127.0.0.1", None, "local", {}, 401),
    ("127.0.0.1", "wrong", "local", {}, 403),
    ("192.0.2.1", "test-owner", "local", {}, 403),
    ("127.0.0.1", "test-owner", "cloud", {}, 503),
    ("127.0.0.1", "test-owner", "local", {"command": "echo unsafe"}, 422),
    ("127.0.0.1", "test-owner", "local", {"executable": "/bin/sh"}, 422),
    ("127.0.0.1", "test-owner", "local", {"argv": ["-c", "echo unsafe"]}, 422),
    ("127.0.0.1", "test-owner", "local", {"cwd": "/tmp"}, 422),
    ("127.0.0.1", "test-owner", "local", {"env": {"PATH": "/tmp"}}, 422),
    ("127.0.0.1", "test-owner", "local", {"timeout": 100000}, 422),
])
async def test_policy_denial_never_launches(monkeypatch, host, token, mode, body, status):
    monkeypatch.setenv("AION_RUNTIME_MODE", mode)

    async def forbidden(*args, **kwargs):
        pytest.fail("Policy-denied job launched")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(host, 123)), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await client.post("/local-executive/validate", json=body, headers=headers)
    assert response.status_code == status


async def test_authorized_http_job():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://test") as client:
        response = await client.post("/local-executive/validate", json={}, headers={"Authorization": "Bearer test-owner"})
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


async def test_query_parameters_are_rejected(monkeypatch):
    async def forbidden():
        pytest.fail("Parameterized job launched")

    monkeypatch.setattr(validation, "run_validation", forbidden)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 123)), base_url="http://test") as client:
        response = await client.post("/local-executive/validate?cwd=/tmp", json={}, headers={"Authorization": "Bearer test-owner"})
    assert response.status_code == 400


async def test_disconnect_cancels_and_cleans_tree(process_tree, monkeypatch):
    from fastapi import HTTPException, Request
    from aion.main import LocalValidationRequest, local_executive_validate

    request = Request({"type": "http", "client": ("127.0.0.1", 123), "headers": [], "query_string": b""})

    async def disconnected():
        return process_tree.exists()

    monkeypatch.setattr(request, "is_disconnected", disconnected)
    with pytest.raises(HTTPException) as exc:
        await asyncio.wait_for(local_executive_validate(LocalValidationRequest(), request, "Bearer test-owner"), 5)
    assert exc.value.status_code == 499
    await assert_tree_stopped(process_tree)


async def test_http_timeout_drains_watcher_and_cleans_tree(process_tree, monkeypatch, endpoint_tasks_are_drained):
    from fastapi import Request
    from aion.main import LocalValidationRequest, local_executive_validate

    request = Request({"type": "http", "client": ("127.0.0.1", 123), "headers": [], "query_string": b""})

    async def connected():
        return False

    monkeypatch.setattr(request, "is_disconnected", connected)
    monkeypatch.setattr(validation, "TIMEOUT_SECONDS", 2)
    result = await asyncio.wait_for(local_executive_validate(LocalValidationRequest(), request, "Bearer test-owner"), 5)
    assert result["status"] == "timeout"
    assert len(endpoint_tasks_are_drained) == 2
    assert all(task.done() for task in endpoint_tasks_are_drained)
    await assert_tree_stopped(process_tree)


async def test_disconnect_during_startup_cleans_tree(process_tree, monkeypatch):
    from fastapi import HTTPException, Request
    from aion.main import LocalValidationRequest, local_executive_validate

    real_spawn = asyncio.create_subprocess_exec
    release = asyncio.Event()
    detected = asyncio.Event()

    async def slow_spawn(*args, **kwargs):
        process = await real_spawn(*args, **kwargs)
        await release.wait()
        return process

    request = Request({"type": "http", "client": ("127.0.0.1", 123), "headers": [], "query_string": b""})

    async def disconnected():
        if process_tree.exists():
            detected.set()
            return True
        return False

    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_spawn)
    monkeypatch.setattr(request, "is_disconnected", disconnected)
    task = asyncio.create_task(local_executive_validate(LocalValidationRequest(), request, "Bearer test-owner"))
    try:
        await wait_ready(process_tree)
        await asyncio.wait_for(detected.wait(), 5)
        await asyncio.sleep(0.05)
        assert not task.done()  # Disconnect waits for pending spawn cleanup.
    finally:
        release.set()
    with pytest.raises(HTTPException) as exc:
        await asyncio.wait_for(task, 5)
    assert exc.value.status_code == 499
    await assert_tree_stopped(process_tree)
