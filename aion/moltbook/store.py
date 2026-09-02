"""Phase 2 persistence for approvals, audits, leads, and risk state.

Backed by durable SQLite by default, or Postgres schema ``aion`` when
``AION_DATABASE_URL`` is configured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from aion.durable.db import connect_phase2, database_url
from aion.moltbook.security import utc_now_iso


def default_phase2_db_path() -> str:
    """Prefer durable AION_DATA_DIR; fall back to legacy /tmp only if unset fails."""
    try:
        from aion.durable.paths import resolve_durable_paths

        return str(resolve_durable_paths().phase2_db)
    except Exception:
        return "/tmp/aion_phase2.db"


DEFAULT_DB_PATH = "/tmp/aion_phase2.db"  # legacy; prefer default_phase2_db_path()


class Phase2Store:
    """Append-friendly store. Audit rows are never updated or deleted."""

    def __init__(self, path: str | None = None, *, connection: Any | None = None):
        self.path = path or default_phase2_db_path()
        if not database_url():
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = connection or connect_phase2(self.path)
        self.backend = getattr(self._conn, "backend", "sqlite")
        self._init_schema()

    def _init_schema(self) -> None:
        # Postgres schema is applied via migrations; SQLite still bootstraps locally.
        if getattr(self._conn, "backend", "sqlite") == "postgres":
            return
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS approvals (
              request_id TEXT PRIMARY KEY,
              action TEXT NOT NULL,
              summary TEXT NOT NULL,
              destination TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              idempotency_key TEXT UNIQUE,
              decision TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              decided_at TEXT,
              decided_by TEXT,
              reason TEXT,
              approval_token_hash TEXT,
              token_consumed_at TEXT,
              executed_at TEXT,
              injection_flags_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS audit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              module TEXT NOT NULL,
              action TEXT NOT NULL,
              success INTEGER NOT NULL,
              detail_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leads (
              lead_id TEXT PRIMARY KEY,
              source_url TEXT NOT NULL,
              requester_identity TEXT NOT NULL,
              stated_problem TEXT NOT NULL,
              relevant_service TEXT NOT NULL,
              fit_score REAL NOT NULL,
              confidence_score REAL NOT NULL,
              suggested_response TEXT NOT NULL,
              risks TEXT NOT NULL,
              approval_status TEXT NOT NULL,
              conversion_outcome TEXT NOT NULL,
              revenue_attributed REAL NOT NULL DEFAULT 0,
              raw_excerpt TEXT NOT NULL,
              created_at TEXT NOT NULL,
              content_hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS drafts (
              draft_id TEXT PRIMARY KEY,
              day_index INTEGER NOT NULL,
              theme TEXT NOT NULL,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              submolt TEXT NOT NULL,
              yalitek_connection TEXT,
              approval_request_id TEXT,
              created_at TEXT NOT NULL,
              content_hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS risk_state (
              key TEXT PRIMARY KEY,
              value_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- approvals -----------------------------------------------------------

    def upsert_approval(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO approvals (
              request_id, action, summary, destination, payload_json, content_hash,
              idempotency_key, decision, created_at, expires_at, decided_at, decided_by,
              reason, approval_token_hash, token_consumed_at, executed_at,
              injection_flags_json
            ) VALUES (
              :request_id, :action, :summary, :destination, :payload_json, :content_hash,
              :idempotency_key, :decision, :created_at, :expires_at, :decided_at, :decided_by,
              :reason, :approval_token_hash, :token_consumed_at, :executed_at,
              :injection_flags_json
            )
            ON CONFLICT(request_id) DO UPDATE SET
              decision=excluded.decision,
              decided_at=excluded.decided_at,
              decided_by=excluded.decided_by,
              reason=excluded.reason,
              approval_token_hash=excluded.approval_token_hash,
              token_consumed_at=excluded.token_consumed_at,
              executed_at=excluded.executed_at
            """,
            row,
        )
        self._conn.commit()

    def get_approval(self, request_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute(
            "SELECT * FROM approvals WHERE request_id = ?", (request_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_approval_by_idempotency(self, key: str) -> dict[str, Any] | None:
        cur = self._conn.execute(
            "SELECT * FROM approvals WHERE idempotency_key = ?", (key,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def list_approvals(self, *, decision: str | None = None) -> list[dict[str, Any]]:
        if decision:
            cur = self._conn.execute(
                "SELECT * FROM approvals WHERE decision = ? ORDER BY created_at DESC",
                (decision,),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM approvals ORDER BY created_at DESC"
            )
        return [dict(r) for r in cur.fetchall()]

    def count_approvals_since(self, *, action: str, since_iso: str, decisions: Iterable[str]) -> int:
        placeholders = ",".join("?" for _ in decisions)
        params = [action, since_iso, *decisions]
        cur = self._conn.execute(
            f"""
            SELECT COUNT(*) AS c FROM approvals
            WHERE action = ?
              AND created_at >= ?
              AND decision IN ({placeholders})
            """,
            params,
        )
        return int(cur.fetchone()["c"])

    # --- audit ---------------------------------------------------------------

    def append_audit(self, *, module: str, action: str, success: bool, detail: dict[str, Any]) -> int:
        if getattr(self._conn, "backend", "sqlite") == "postgres":
            cur = self._conn.execute(
                """
                INSERT INTO audit_events (timestamp, module, action, success, detail_json)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    utc_now_iso(),
                    module,
                    action,
                    bool(success),
                    json.dumps(detail, default=str),
                ),
            )
            row = cur.fetchone()
            self._conn.commit()
            return int(row["id"] if isinstance(row, dict) else row[0])

        cur = self._conn.execute(
            """
            INSERT INTO audit_events (timestamp, module, action, success, detail_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                module,
                action,
                1 if success else 0,
                json.dumps(detail, default=str),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_audit(self, *, limit: int = 100) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM audit_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = []
        for row in cur.fetchall():
            item = dict(row)
            item["detail"] = json.loads(item.pop("detail_json"))
            item["success"] = bool(item["success"])
            rows.append(item)
        return rows

    # --- leads / drafts ------------------------------------------------------

    def upsert_lead(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO leads (
              lead_id, source_url, requester_identity, stated_problem, relevant_service,
              fit_score, confidence_score, suggested_response, risks, approval_status,
              conversion_outcome, revenue_attributed, raw_excerpt, created_at, content_hash
            ) VALUES (
              :lead_id, :source_url, :requester_identity, :stated_problem, :relevant_service,
              :fit_score, :confidence_score, :suggested_response, :risks, :approval_status,
              :conversion_outcome, :revenue_attributed, :raw_excerpt, :created_at, :content_hash
            )
            ON CONFLICT(content_hash) DO UPDATE SET
              source_url=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.source_url ELSE leads.source_url END,
              requester_identity=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.requester_identity ELSE leads.requester_identity END,
              stated_problem=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.stated_problem ELSE leads.stated_problem END,
              relevant_service=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.relevant_service ELSE leads.relevant_service END,
              fit_score=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.fit_score ELSE leads.fit_score END,
              confidence_score=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.confidence_score ELSE leads.confidence_score END,
              suggested_response=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.suggested_response ELSE leads.suggested_response END,
              risks=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.risks ELSE leads.risks END,
              raw_excerpt=CASE WHEN leads.approval_status = 'pending_owner_review' THEN excluded.raw_excerpt ELSE leads.raw_excerpt END
            """,
            row,
        )
        self._conn.commit()

    def list_leads(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM leads ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

    def upsert_draft(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO drafts (
              draft_id, day_index, theme, title, body, submolt, yalitek_connection,
              approval_request_id, created_at, content_hash
            ) VALUES (
              :draft_id, :day_index, :theme, :title, :body, :submolt, :yalitek_connection,
              :approval_request_id, :created_at, :content_hash
            )
            ON CONFLICT(content_hash) DO UPDATE SET
              approval_request_id=COALESCE(excluded.approval_request_id, drafts.approval_request_id)
            """,
            row,
        )
        self._conn.commit()

    def update_draft_approval(self, draft_id: str, approval_request_id: str) -> None:
        self._conn.execute(
            "UPDATE drafts SET approval_request_id = ? WHERE draft_id = ?",
            (approval_request_id, draft_id),
        )
        self._conn.commit()

    def list_drafts(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM drafts ORDER BY day_index ASC")
        return [dict(r) for r in cur.fetchall()]

    def set_risk(self, key: str, value: Any) -> None:
        self._conn.execute(
            """
            INSERT INTO risk_state (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value_json=excluded.value_json,
              updated_at=excluded.updated_at
            """,
            (key, json.dumps(value, default=str), utc_now_iso()),
        )
        self._conn.commit()

    def get_risk(self, key: str, default: Any = None) -> Any:
        cur = self._conn.execute(
            "SELECT value_json FROM risk_state WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        if not row:
            return default
        return json.loads(row["value_json"])

    def list_risk_prefix(self, prefix: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT key, value_json, updated_at FROM risk_state WHERE key LIKE ? ORDER BY updated_at DESC",
            (f"{prefix}%",),
        )
        rows = []
        for row in cur.fetchall():
            item = dict(row)
            rows.append({
                "key": item["key"],
                "value": json.loads(item["value_json"]),
                "updated_at": item["updated_at"],
            })
        return rows
