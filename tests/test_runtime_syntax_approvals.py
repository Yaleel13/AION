from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3
import threading
import time

import pytest

from aion.moltbook.store import Phase2Store, RUNTIME_SYNTAX_CAPABILITY

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def create_pending(store: Phase2Store, *, expires_at: datetime | None = None) -> str:
    return store.create_runtime_syntax_approval(
        requester_principal="agent:local-test",
        expires_at=expires_at or NOW + timedelta(minutes=5),
        created_at=NOW,
    )


def approve(store: Phase2Store, execution_request_id: str) -> None:
    assert store.decide_runtime_syntax_approval(
        execution_request_id,
        approved=True,
        decided_by="owner:test",
        now=NOW,
    )


def test_pending_and_denied_approvals_cannot_be_claimed(tmp_path: Path) -> None:
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))
    pending = create_pending(store)
    assert re.fullmatch(r"[0-9a-f]{32}", pending)
    assert not store.claim_runtime_syntax_approval(
        pending,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW,
    ).claimed

    denied = create_pending(store)
    assert store.decide_runtime_syntax_approval(
        denied,
        approved=False,
        decided_by="owner:test",
        now=NOW,
    )
    assert not store.claim_runtime_syntax_approval(
        denied,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW,
    ).claimed


def test_claim_requires_exact_capability_and_requester_binding(tmp_path: Path) -> None:
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))
    execution_request_id = create_pending(store)
    approve(store, execution_request_id)

    assert not store.claim_runtime_syntax_approval(
        execution_request_id,
        capability="runtime_status",
        requester_principal="agent:local-test",
        now=NOW,
    ).claimed
    assert not store.claim_runtime_syntax_approval(
        execution_request_id,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:other",
        now=NOW,
    ).claimed
    assert store.claim_runtime_syntax_approval(
        execution_request_id,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW,
    ).claimed


def test_expiry_boundary_is_denied(tmp_path: Path) -> None:
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))
    execution_request_id = create_pending(store, expires_at=NOW)
    assert not store.decide_runtime_syntax_approval(
        execution_request_id,
        approved=True,
        decided_by="owner:test",
        now=NOW,
    )

    execution_request_id = create_pending(store, expires_at=NOW + timedelta(seconds=1))
    approve(store, execution_request_id)
    assert not store.claim_runtime_syntax_approval(
        execution_request_id,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW + timedelta(seconds=1),
    ).claimed


def test_claim_replay_is_denied(tmp_path: Path) -> None:
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))
    execution_request_id = create_pending(store)
    approve(store, execution_request_id)
    first = store.claim_runtime_syntax_approval(
        execution_request_id,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW,
    )
    replay = store.claim_runtime_syntax_approval(
        execution_request_id,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW,
    )
    assert first.claimed
    assert not replay.claimed
    row = store._conn.execute(
        "SELECT decision, consumed_at, consumed_by FROM runtime_syntax_approvals WHERE execution_request_id = ?",
        (execution_request_id,),
    ).fetchone()
    assert dict(row) == {
        "decision": "approved",
        "consumed_at": NOW.isoformat(),
        "consumed_by": "agent:local-test",
    }


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("execution_request_id", "f" * 32),
        ("capability", "runtime_status"),
        ("requester_principal", "agent:changed"),
    ],
)
def test_approved_bindings_are_immutable(tmp_path: Path, column: str, value: str) -> None:
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))
    execution_request_id = create_pending(store)
    approve(store, execution_request_id)

    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute(
            f"UPDATE runtime_syntax_approvals SET {column} = ? WHERE execution_request_id = ?",
            (value, execution_request_id),
        )
    store._conn.rollback()


def test_storage_error_denies_claim(tmp_path: Path) -> None:
    store = Phase2Store(str(tmp_path / "approvals.sqlite3"))

    class UnavailableConnection:
        def execute(self, *_args, **_kwargs):
            raise OSError("database unavailable")

        def commit(self):
            raise OSError("database unavailable")

        def rollback(self):
            raise OSError("database unavailable")

    store._conn = UnavailableConnection()
    claim = store.claim_runtime_syntax_approval(
        "0" * 32,
        capability=RUNTIME_SYNTAX_CAPABILITY,
        requester_principal="agent:local-test",
        now=NOW,
    )
    assert not claim.claimed
    assert claim.reason == "storage_unavailable"


def test_claim_rechecks_expiry_after_waiting_for_a_database_lock(tmp_path: Path) -> None:
    path = str(tmp_path / "approvals.sqlite3")
    owner_store = Phase2Store(path)
    now = datetime.now(timezone.utc)
    execution_request_id = create_pending(owner_store, expires_at=now + timedelta(milliseconds=200))
    assert owner_store.decide_runtime_syntax_approval(
        execution_request_id,
        approved=True,
        decided_by="owner:test",
        now=now,
    )
    lock_store = Phase2Store(path)
    claimant_store = Phase2Store(path)
    lock_store._conn.begin_immediate()
    claim_started = threading.Event()

    def claim() -> bool:
        claim_started.set()
        return claimant_store.claim_runtime_syntax_approval(
            execution_request_id,
            capability=RUNTIME_SYNTAX_CAPABILITY,
            requester_principal="agent:local-test",
        ).claimed

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(claim)
        assert claim_started.wait(timeout=1)
        time.sleep(0.3)
        lock_store._conn.commit()
        assert not future.result(timeout=5)


def test_two_independent_connections_can_claim_only_once(tmp_path: Path) -> None:
    path = str(tmp_path / "approvals.sqlite3")
    owner_store = Phase2Store(path)
    execution_request_id = create_pending(owner_store)
    approve(owner_store, execution_request_id)
    first_store = Phase2Store(path)
    second_store = Phase2Store(path)

    def claim(store: Phase2Store) -> bool:
        return store.claim_runtime_syntax_approval(
            execution_request_id,
            capability=RUNTIME_SYNTAX_CAPABILITY,
            requester_principal="agent:local-test",
            now=NOW,
        ).claimed

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, (first_store, second_store)))

    assert results.count(True) == 1
    assert results.count(False) == 1
