"""Scheduler lock, cycle health, and missed-cycle alerts (SQLite)."""

from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from typing import Any
from uuid import uuid4

from aion.moltbook.security import utc_now, utc_now_iso
from aion.moltbook.store import Phase2Store


class SchedulerStore:
    """Distributed-ish locking and health state on the durable Phase2 DB."""

    def __init__(self, store: Phase2Store):
        self.store = store
        self._conn = store._conn
        self._init()

    def _init(self) -> None:
        if getattr(self._conn, "backend", "sqlite") == "postgres":
            return
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scheduler_locks (
              lock_name TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              acquired_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              meta_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS scheduler_state (
              key TEXT PRIMARY KEY,
              value_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS health_alerts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              alert_type TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              delivered INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        self._conn.commit()

    def try_acquire_lock(
        self,
        lock_name: str,
        *,
        owner_id: str | None = None,
        ttl_seconds: int = 900,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Acquire named lock if free or expired. Prevents overlapping cycles."""
        owner = owner_id or str(uuid4())
        now = utc_now()
        expires = now + timedelta(seconds=ttl_seconds)
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            row = cur.execute(
                "SELECT owner_id, expires_at FROM scheduler_locks WHERE lock_name=?",
                (lock_name,),
            ).fetchone()
            if row:
                exp = row["expires_at"]
                # Expired → steal; same owner → renew; else deny.
                from datetime import datetime

                exp_dt = datetime.fromisoformat(exp)
                if exp_dt.tzinfo is None:
                    from datetime import timezone

                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if exp_dt > now and row["owner_id"] != owner:
                    self._conn.rollback()
                    return {
                        "acquired": False,
                        "reason": "held",
                        "holder": row["owner_id"],
                        "expires_at": exp,
                    }
            cur.execute(
                """
                INSERT INTO scheduler_locks(lock_name, owner_id, acquired_at, expires_at, meta_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(lock_name) DO UPDATE SET
                  owner_id=excluded.owner_id,
                  acquired_at=excluded.acquired_at,
                  expires_at=excluded.expires_at,
                  meta_json=excluded.meta_json
                """,
                (
                    lock_name,
                    owner,
                    utc_now_iso(),
                    expires.isoformat(),
                    json.dumps(meta or {}, default=str),
                ),
            )
            self._conn.commit()
            return {
                "acquired": True,
                "owner_id": owner,
                "expires_at": expires.isoformat(),
                "lock_name": lock_name,
            }
        except Exception:
            self._conn.rollback()
            raise

    def release_lock(self, lock_name: str, owner_id: str) -> bool:
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            row = cur.execute(
                "SELECT owner_id FROM scheduler_locks WHERE lock_name=?",
                (lock_name,),
            ).fetchone()
            if not row or row["owner_id"] != owner_id:
                self._conn.rollback()
                return False
            cur.execute("DELETE FROM scheduler_locks WHERE lock_name=?", (lock_name,))
            self._conn.commit()
            return True
        except Exception:
            self._conn.rollback()
            raise

    def set_state(self, key: str, value: Any) -> None:
        self._conn.execute(
            """
            INSERT INTO scheduler_state(key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value_json=excluded.value_json,
              updated_at=excluded.updated_at
            """,
            (key, json.dumps(value, default=str), utc_now_iso()),
        )
        self._conn.commit()

    def get_state(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value_json FROM scheduler_state WHERE key=?", (key,)
        ).fetchone()
        if not row:
            return default
        return json.loads(row["value_json"])

    def record_cycle_result(self, result: dict[str, Any]) -> None:
        history = self.get_state("cycle_history", [])
        if not isinstance(history, list):
            history = []
        entry = {
            "timestamp": utc_now_iso(),
            "success": bool(result.get("success", True)),
            "skipped": result.get("skipped"),
            "error": result.get("error"),
            "actions": result.get("actions"),
        }
        history = [entry, *history][:50]
        self.set_state("cycle_history", history)
        self.set_state("last_cycle", entry)
        if entry["success"]:
            self.set_state("last_success_at", entry["timestamp"])
            self.set_state("consecutive_failures", 0)
        else:
            fails = int(self.get_state("consecutive_failures", 0) or 0) + 1
            self.set_state("consecutive_failures", fails)

    def log_health_alert(self, alert_type: str, detail: dict[str, Any]) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO health_alerts(timestamp, alert_type, detail_json, delivered)
            VALUES (?, ?, ?, 0)
            """,
            (utc_now_iso(), alert_type, json.dumps(detail, default=str)),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_undelivered_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM health_alerts WHERE delivered=0
            ORDER BY id ASC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["detail"] = json.loads(item.pop("detail_json"))
            out.append(item)
        return out

    def mark_alert_delivered(self, alert_id: int) -> None:
        self._conn.execute(
            "UPDATE health_alerts SET delivered=1 WHERE id=?", (alert_id,)
        )
        self._conn.commit()
