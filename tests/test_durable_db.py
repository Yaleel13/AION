"""Durable DB factory — SQLite default, Postgres when URL configured."""

from __future__ import annotations

import os

from aion.durable.db import connect_phase2, storage_backend, storage_status
from aion.moltbook.store import Phase2Store


def test_storage_backend_defaults_to_sqlite(monkeypatch, tmp_path):
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    assert storage_backend() == "sqlite"
    status = storage_status()
    assert status.backend == "sqlite"
    assert status.configured is True


def test_phase2_store_sqlite_roundtrip(monkeypatch, tmp_path):
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    db = tmp_path / "phase2.db"
    store = Phase2Store(str(db))
    assert store.backend == "sqlite"
    store.set_risk("probe", {"ok": True})
    assert store.get_risk("probe") == {"ok": True}
    audit_id = store.append_audit(
        module="test", action="probe", success=True, detail={"src": "unit"}
    )
    assert audit_id >= 1
    rows = store.list_audit(limit=5)
    assert rows and rows[0]["action"] == "probe"
    store.close()
