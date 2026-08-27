"""Atomic rolling counters, pacing, account caps, and experiment state."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from aion.moltbook.autonomy_policy import ExperimentLimits, primary_topic
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
        if getattr(self._conn, "backend", "sqlite") == "postgres":
            return
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

            CREATE TABLE IF NOT EXISTS autonomy_account_interactions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              account TEXT NOT NULL,
              action TEXT NOT NULL,
              solicited INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS autonomy_rate_limits (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              action TEXT,
              status_code INTEGER,
              retry_after_seconds REAL,
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
        if getattr(self._conn, "backend", "sqlite") == "postgres":
            return
        # Non-destructive migrations for DBs created before text_norm/account columns.
        cols = {
            r[1]
            for r in self._conn.execute("PRAGMA table_info(autonomy_actions)").fetchall()
        }
        if "text_norm" not in cols:
            self._conn.execute("ALTER TABLE autonomy_actions ADD COLUMN text_norm TEXT")
        if "account" not in cols:
            self._conn.execute("ALTER TABLE autonomy_actions ADD COLUMN account TEXT")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_autonomy_actions_time ON autonomy_actions(timestamp)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_autonomy_actions_account "
            "ON autonomy_actions(account, timestamp)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_autonomy_account_time "
            "ON autonomy_account_interactions(account, created_at)"
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
        oldest = self._conn.execute(
            """
            SELECT MIN(created_at) AS oldest FROM autonomy_quota_events
            WHERE action=? AND created_at >= ?
            """,
            (action, since),
        ).fetchone()
        return {
            "window_hours": window_hours,
            "action": action,
            "count": int(row["c"]) if row else 0,
            "since": since,
            "oldest": oldest["oldest"] if oldest else None,
        }

    def last_action_at(self, action: str) -> datetime | None:
        row = self._conn.execute(
            """
            SELECT created_at FROM autonomy_quota_events
            WHERE action=? ORDER BY id DESC LIMIT 1
            """,
            (action,),
        ).fetchone()
        if not row or not row["created_at"]:
            return None
        ts = datetime.fromisoformat(row["created_at"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts

    def count_actions_since(self, action: str, *, seconds: int) -> int:
        since = (utc_now() - timedelta(seconds=seconds)).isoformat()
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS c FROM autonomy_quota_events
            WHERE action=? AND created_at >= ?
            """,
            (action, since),
        ).fetchone()
        return int(row["c"]) if row else 0

    def assert_pacing(self, action: str, limits: ExperimentLimits) -> None:
        """Raise OverflowError with a pacing reason if cooldown/hourly caps block."""
        now = utc_now()
        last = self.last_action_at(action)
        if action == "create_post":
            min_gap = limits.min_seconds_between_posts
            if last and (now - last).total_seconds() < min_gap:
                raise OverflowError(
                    f"pacing_cooldown:create_post need {min_gap}s between posts"
                )
        elif action == "comment":
            min_gap = limits.min_seconds_between_comments
            if last and (now - last).total_seconds() < min_gap:
                raise OverflowError(
                    f"pacing_cooldown:comment need {min_gap}s between comments"
                )
            hourly = self.count_actions_since("comment", seconds=3600)
            if hourly >= limits.max_comments_per_hour:
                raise OverflowError(
                    f"pacing_hourly:comment max {limits.max_comments_per_hour}/hour"
                )
        elif action == "follow":
            min_gap = limits.min_seconds_between_follows
            if last and (now - last).total_seconds() < min_gap:
                raise OverflowError(
                    f"pacing_cooldown:follow need {min_gap}s between follows "
                    "(no rapid follow bursts)"
                )
            hourly = self.count_actions_since("follow", seconds=3600)
            if hourly >= limits.max_follows_per_hour:
                raise OverflowError(
                    f"pacing_hourly:follow max {limits.max_follows_per_hour}/hour"
                )

    def count_unsolicited_account_interactions(
        self, account: str, *, hours: int = 24
    ) -> int:
        since = (utc_now() - timedelta(hours=hours)).isoformat()
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS c FROM autonomy_account_interactions
            WHERE account=? AND solicited=0 AND created_at >= ?
            """,
            (account.lower(), since),
        ).fetchone()
        return int(row["c"]) if row else 0

    def record_account_interaction(
        self, account: str, *, action: str, solicited: bool = False
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO autonomy_account_interactions(account, action, solicited, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (account.lower(), action, 1 if solicited else 0, utc_now_iso()),
        )
        self._conn.commit()

    def assert_account_cap(
        self,
        account: str | None,
        *,
        limits: ExperimentLimits,
        solicited: bool = False,
    ) -> None:
        if not account or solicited:
            return
        count = self.count_unsolicited_account_interactions(account, hours=24)
        if count >= limits.max_unsolicited_per_account_24h:
            raise OverflowError(
                f"per_account_cap:{account} "
                f"max {limits.max_unsolicited_per_account_24h} unsolicited/24h"
            )

    def recent_texts(self, *, hours: int = 24 * 14, action: str | None = None) -> list[str]:
        since = (utc_now() - timedelta(hours=hours)).isoformat()
        if action:
            rows = self._conn.execute(
                """
                SELECT text_norm FROM autonomy_actions
                WHERE timestamp >= ? AND success=1 AND text_norm IS NOT NULL AND action=?
                ORDER BY id DESC LIMIT 40
                """,
                (since, action),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT text_norm FROM autonomy_actions
                WHERE timestamp >= ? AND success=1 AND text_norm IS NOT NULL
                ORDER BY id DESC LIMIT 40
                """,
                (since,),
            ).fetchall()
        return [r["text_norm"] for r in rows if r["text_norm"]]

    def recent_post_topics(self, *, hours: int = 24 * 14) -> list[str]:
        texts = self.recent_texts(hours=hours, action="create_post")
        out: list[str] = []
        for text in texts:
            topic = primary_topic(text)
            if topic:
                out.append(topic)
        return out

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
        text_norm: str | None = None,
        account: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO autonomy_actions(
              timestamp, action, destination, content_hash, idempotency_key, url,
              success, detail_json, text_norm, account
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                text_norm,
                account.lower() if account else None,
            ),
        )
        self._conn.commit()

    def log_rate_limit(
        self,
        *,
        action: str | None,
        status_code: int,
        retry_after_seconds: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO autonomy_rate_limits(
              timestamp, action, status_code, retry_after_seconds, detail_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                action,
                status_code,
                retry_after_seconds,
                json.dumps(detail or {}, default=str),
            ),
        )
        self._conn.commit()

    def list_rate_limits_since(self, since_iso: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM autonomy_rate_limits WHERE timestamp >= ? ORDER BY id DESC
            """,
            (since_iso,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["detail"] = json.loads(item.pop("detail_json"))
            out.append(item)
        return out

    def has_idempotency(self, key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM autonomy_actions WHERE idempotency_key=?", (key,)
        ).fetchone()
        return row is not None

    def recent_content_hashes(self, *, hours: int = 24 * 14) -> set[str]:
        since = (utc_now() - timedelta(hours=hours)).isoformat()
        rows = self._conn.execute(
            """
            SELECT content_hash FROM autonomy_actions
            WHERE timestamp >= ? AND success=1
            """,
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

    def list_follows_since(self, since_iso: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM autonomy_actions
            WHERE action='follow' AND timestamp >= ? ORDER BY id DESC
            """,
            (since_iso,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["success"] = bool(item["success"])
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

    def quota_availability(self, limits: ExperimentLimits) -> dict[str, Any]:
        posts = self.get_counter("create_post", window_hours=24)
        comments = self.get_counter("comment", window_hours=24)
        follows = self.get_counter("follow", window_hours=24 * 7)
        comments_hour = self.count_actions_since("comment", seconds=3600)
        follows_hour = self.count_actions_since("follow", seconds=3600)
        return {
            "create_post": {
                **posts,
                "limit": limits.max_posts_per_24h,
                "remaining": max(0, limits.max_posts_per_24h - posts["count"]),
            },
            "comment": {
                **comments,
                "limit": limits.max_comments_per_24h,
                "remaining": max(0, limits.max_comments_per_24h - comments["count"]),
                "hourly_count": comments_hour,
                "hourly_limit": limits.max_comments_per_hour,
            },
            "follow": {
                **follows,
                "limit": limits.max_follows_per_7d,
                "remaining": max(0, limits.max_follows_per_7d - follows["count"]),
                "hourly_count": follows_hour,
                "hourly_limit": limits.max_follows_per_hour,
            },
        }
