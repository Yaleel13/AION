"""Atomic rolling counters, blocked-action log, and experiment state for controlled autonomy."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from aion.moltbook.security import utc_now, utc_now_iso
from aion.moltbook.store import Phase2Store


class AutonomyStore:
    """Extends Phase2 SQLite with atomic rolling quota counters and block logs."""

    def __init__(self, store: Phase2Store):
        self.store = store
        self.path = store.path
        self._conn = store._conn
        self._init()

    def _init(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS autonomy_quota_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              action TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_autonomy_quota_action_time
              ON autonomy_quota_events(action, created_at);

            CREATE TABLE IF NOT EXISTS autonomy_blocks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              action TEXT NOT NULL,
              reasons_json TEXT NOT NULL,
              payload_hash TEXT,
              detail_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autonomy_actions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              action TEXT NOT NULL,
              destination TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              idempotency_key TEXT UNIQUE,
              url TEXT,
              success INTEGER NOT NULL,
              detail_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_reports (
              report_date TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              body_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lead_alerts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              lead_id TEXT NOT NULL,
              detail_json TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def increment_counter(self, action: str, *, limit: int, window_hours: int) -> int:
        """Atomically reserve one quota slot in a rolling window; raise if at limit."""
        now = utc_now()
        since = (now - timedelta(hours=window_hours)).isoformat()
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.execute(
                "DELETE FROM autonomy_quota_events WHERE action=? AND created_at < ?",
                (action, since),
            )
            row = cur.execute(
                """
                SELECT COUNT(*) AS c FROM autonomy_quota_events
                WHERE action=? AND created_at >= ?
                """,
                (action, since),
            ).fetchone()
            current = int(row["c"]) if row else 0
            if current >= limit:
                self._conn.rollback()
                raise OverflowError(
                    f"limit reached for {action} in rolling {window_hours}h: {limit}"
                )
            new_count = current + 1
            cur.execute(
                "INSERT INTO autonomy_quota_events(action, created_at) VALUES (?, ?)",
                (action, utc_now_iso()),
            )
            self._conn.commit()
            return new_count
        except Exception:
            self._conn.rollback()
            raise

    def refund_last_quota(self, action: str) -> bool:
        """Remove the most recent quota reservation for action (failed live attempt)."""
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            row = cur.execute(
                """
                SELECT id FROM autonomy_quota_events
                WHERE action=? ORDER BY id DESC LIMIT 1
                """,
                (action,),
            ).fetchone()
            if not row:
                self._conn.rollback()
                return False
            cur.execute("DELETE FROM autonomy_quota_events WHERE id=?", (row["id"],))
            self._conn.commit()
            return True
        except Exception:
            self._conn.rollback()
            raise

    def get_counter(self, action: str, *, window_hours: int) -> dict[str, Any]:
        since = (utc_now() - timedelta(hours=window_hours)).isoformat()
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS c FROM autonomy_quota_events
            WHERE action=? AND created_at >= ?
            """,
            (action, since),
        ).fetchone()
        return {
            "window_hours": window_hours,
            "action": action,
            "count": int(row["c"]) if row else 0,
            "since": since,
        }

    def log_block(
        self,
        *,
        action: str,
        reasons: list[str],
        payload_hash: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO autonomy_blocks(timestamp, action, reasons_json, payload_hash, detail_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                action,
                json.dumps(reasons),
                payload_hash,
                json.dumps(detail or {}, default=str),
            ),
        )
        self._conn.commit()

    def log_action(
        self,
        *,
        action: str,
        destination: str,
        content_hash: str,
        idempotency_key: str,
        success: bool,
        url: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO autonomy_actions(
              timestamp, action, destination, content_hash, idempotency_key, url, success, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                action,
                destination,
                content_hash,
                idempotency_key,
                url,
                1 if success else 0,
                json.dumps(detail or {}, default=str),
            ),
        )
        self._conn.commit()

    def has_idempotency(self, key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM autonomy_actions WHERE idempotency_key=?", (key,)
        ).fetchone()
        return row is not None

    def recent_content_hashes(self, *, hours: int = 24 * 14) -> set[str]:
        since = (utc_now() - timedelta(hours=hours)).isoformat()
        rows = self._conn.execute(
            "SELECT content_hash FROM autonomy_actions WHERE timestamp >= ?",
            (since,),
        ).fetchall()
        return {r["content_hash"] for r in rows}

    def list_actions_since(self, since_iso: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM autonomy_actions WHERE timestamp >= ? ORDER BY id DESC",
            (since_iso,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["success"] = bool(item["success"])
            item["detail"] = json.loads(item.pop("detail_json"))
            out.append(item)
        return out

    def list_blocks_since(self, since_iso: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM autonomy_blocks WHERE timestamp >= ? ORDER BY id DESC",
            (since_iso,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["reasons"] = json.loads(item.pop("reasons_json"))
            item["detail"] = json.loads(item.pop("detail_json"))
            out.append(item)
        return out

    def save_daily_report(self, report_date: str, body: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO daily_reports(report_date, created_at, body_json)
            VALUES (?, ?, ?)
            ON CONFLICT(report_date) DO UPDATE SET
              body_json=excluded.body_json,
              created_at=excluded.created_at
            """,
            (report_date, utc_now_iso(), json.dumps(body, default=str)),
        )
        self._conn.commit()

    def log_lead_alert(self, lead_id: str, detail: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO lead_alerts(timestamp, lead_id, detail_json)
            VALUES (?, ?, ?)
            """,
            (utc_now_iso(), lead_id, json.dumps(detail, default=str)),
        )
        self._conn.commit()

    def list_lead_alerts_since(self, since_iso: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM lead_alerts WHERE timestamp >= ? ORDER BY id DESC",
            (since_iso,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["detail"] = json.loads(item.pop("detail_json"))
            out.append(item)
        return out
