"""Tests for durable path resolution and non-destructive migration."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from aion.durable.migrate import migrate_to_durable, rollback_from_backup
from aion.durable.paths import resolve_durable_paths
from aion.durable.scheduler_store import SchedulerStore
from aion.moltbook.store import Phase2Store
from aion.moltbook.autonomy_store import AutonomyStore


def _seed_phase2(path: Path) -> None:
    store = Phase2Store(str(path))
    auto = AutonomyStore(store)
    # Reserve quotas without hitting overflow
    auto.increment_counter("create_post", limit=10, window_hours=24)
    auto.increment_counter("create_post", limit=10, window_hours=24)
    auto.increment_counter("comment", limit=10, window_hours=24)
    store.set_risk(
        "autonomy_policy",
        {
            "experiment_started_at": "2026-08-27T09:55:31+00:00",
            "quota_profile": "expanded",
        },
    )
    store.append_audit(module="test", action="seed", success=True, detail={"ok": True})
    store.close()


def test_resolve_durable_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "durable"))
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    monkeypatch.delenv("AION_PAPER_DB", raising=False)
    monkeypatch.delenv("AION_SESSION_DB", raising=False)
    monkeypatch.delenv("AION_ACTIVATION_DIR", raising=False)
    paths = resolve_durable_paths()
    assert paths.phase2_db.parent == paths.root
    assert paths.root.exists()
    assert paths.activation_dir.exists()


def test_migrate_preserves_quota_counters(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "durable"))
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    monkeypatch.delenv("AION_PAPER_DB", raising=False)
    src = tmp_path / "legacy_phase2.db"
    _seed_phase2(src)
    paths = resolve_durable_paths()
    report = migrate_to_durable(paths=paths, phase2_source=src)
    assert report.quota_counts.get("create_post") == 2
    assert report.quota_counts.get("comment") == 1
    assert "autonomy_policy" in report.risk_keys
    store = Phase2Store(str(paths.phase2_db))
    auto = AutonomyStore(store)
    assert auto.get_counter("create_post", window_hours=24)["count"] == 2
    policy = store.get_risk("autonomy_policy")
    assert policy["quota_profile"] == "expanded"
    assert policy["experiment_started_at"] == "2026-08-27T09:55:31+00:00"
    store.close()


def test_migrate_refuses_overwrite_larger_dest(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "durable"))
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    monkeypatch.delenv("AION_PAPER_DB", raising=False)
    paths = resolve_durable_paths()
    large = paths.phase2_db
    _seed_phase2(large)
    conn = sqlite3.connect(str(large))
    conn.execute(
        "INSERT INTO audit_events(timestamp, module, action, success, detail_json) "
        "VALUES ('t','m','a',1,'{}')"
    )
    conn.commit()
    conn.close()
    small = tmp_path / "small.db"
    Phase2Store(str(small)).close()
    report = migrate_to_durable(paths=paths, phase2_source=small)
    assert any("left unchanged" in w for w in report.warnings)
    store = Phase2Store(str(paths.phase2_db))
    auto = AutonomyStore(store)
    assert auto.get_counter("create_post", window_hours=24)["count"] == 2
    store.close()


def test_rollback_restores_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "durable"))
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    monkeypatch.delenv("AION_PAPER_DB", raising=False)
    paths = resolve_durable_paths()
    _seed_phase2(paths.phase2_db)
    other = tmp_path / "other.db"
    store = Phase2Store(str(other))
    store.set_risk("autonomy_policy", {"quota_profile": "reduced"})
    store.close()
    migrate_to_durable(paths=paths, phase2_source=other)
    backup = paths.root / "migration_backups" / "test"
    backup.mkdir(parents=True)
    _seed_phase2(backup / "phase2_before.db")
    result = rollback_from_backup(backup, paths=paths)
    assert result["actions"]
    store = Phase2Store(str(paths.phase2_db))
    assert AutonomyStore(store).get_counter("create_post", window_hours=24)["count"] == 2
    store.close()


def test_scheduler_lock_prevents_overlap(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_DATA_DIR", str(tmp_path / "durable"))
    monkeypatch.delenv("AION_PHASE2_DB", raising=False)
    store = Phase2Store(str(tmp_path / "sched.db"))
    sched = SchedulerStore(store)
    a = sched.try_acquire_lock("experiment_ops", owner_id="worker-a", ttl_seconds=60)
    assert a["acquired"] is True
    b = sched.try_acquire_lock("experiment_ops", owner_id="worker-b", ttl_seconds=60)
    assert b["acquired"] is False
    assert sched.release_lock("experiment_ops", "worker-a") is True
    c = sched.try_acquire_lock("experiment_ops", owner_id="worker-b", ttl_seconds=60)
    assert c["acquired"] is True
    store.close()
