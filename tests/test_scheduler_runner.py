"""Scheduler runner: lock, miss alerts, no catch-up, failure read-only."""

from __future__ import annotations

import pytest

from aion.durable.scheduler_runner import ExperimentOpsScheduler
from aion.durable.scheduler_store import SchedulerStore
from aion.moltbook.security import KillSwitch
from aion.moltbook.store import Phase2Store


@pytest.mark.asyncio
async def test_lock_skips_overlapping_cycle(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    store = Phase2Store(str(tmp_path / "db.sqlite"))
    sched_store = SchedulerStore(store)
    runner = ExperimentOpsScheduler(sched_store, kill_switch=KillSwitch(engaged=False))

    async def boom(**kwargs):
        raise AssertionError("should not run")

    held = sched_store.try_acquire_lock("experiment_ops_cycle", owner_id="other", ttl_seconds=120)
    assert held["acquired"]
    result = await runner.run_once(boom, flush_queue=True, publish_next_draft=True)
    assert result["skipped"] == "lock_held"
    assert result.get("published") is False
    store.close()


@pytest.mark.asyncio
async def test_kill_switch_skips(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    store = Phase2Store(str(tmp_path / "db.sqlite"))
    runner = ExperimentOpsScheduler(
        SchedulerStore(store), kill_switch=KillSwitch(engaged=True, reason="test")
    )

    async def boom(**kwargs):
        raise AssertionError("should not run")

    result = await runner.run_once(boom)
    assert result["skipped"] == "kill_switch_engaged"
    store.close()


@pytest.mark.asyncio
async def test_failures_engage_readonly(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    store = Phase2Store(str(tmp_path / "db.sqlite"))
    runner = ExperimentOpsScheduler(
        SchedulerStore(store),
        kill_switch=KillSwitch(engaged=False),
        fail_readonly_after=2,
    )

    async def fail(**kwargs):
        return {"error": "transient", "published": False}

    r1 = await runner.run_once(fail)
    assert r1["success"] is False
    r2 = await runner.run_once(fail)
    assert r2["success"] is False
    assert r2.get("readonly_engaged")
    flag = runner.scheduler.get_state("force_readonly")
    assert flag["engaged"] is True

    called = {"n": 0}

    async def ok(**kwargs):
        called["n"] += 1
        # Even if caller asks to publish, force_readonly strips flags inside runner
        return {"published": False, "ok": True}

    r3 = await runner.run_once(ok, flush_queue=True, publish_next_draft=True)
    assert called["n"] == 1
    assert r3.get("force_readonly", {}).get("engaged") is True
    store.close()


@pytest.mark.asyncio
async def test_never_allows_catch_up_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    store = Phase2Store(str(tmp_path / "db.sqlite"))
    runner = ExperimentOpsScheduler(
        SchedulerStore(store), kill_switch=KillSwitch(engaged=False)
    )

    async def ok(**kwargs):
        return {"published": False}

    result = await runner.run_once(ok, allow_catch_up=True)  # type: ignore[call-arg]
    assert result["allow_catch_up"] is False
    store.close()
