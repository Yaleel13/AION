"""Phase 2 persistence for approvals, audits, leads, and risk state.

Backed by durable SQLite by default, or Postgres schema ``aion`` when
``AION_DATABASE_URL`` is configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from aion.durable.db import connect_phase2, database_url
from aion.moltbook.security import utc_now_iso

logger = logging.getLogger(__name__)

RUNTIME_SYNTAX_CAPABILITY = "runtime.syntax"


@dataclass(frozen=True, slots=True)
class RuntimeSyntaxApprovalClaim:
    claimed: bool
    reason: str


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

            CREATE TABLE IF NOT EXISTS runtime_syntax_approvals (
              execution_request_id TEXT PRIMARY KEY,
              capability TEXT NOT NULL CHECK (capability = 'runtime.syntax'),
              requester_principal TEXT NOT NULL CHECK (length(trim(requester_principal)) > 0),
              decision TEXT NOT NULL CHECK (decision IN ('pending', 'approved', 'denied')),
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              decided_at TEXT,
              decided_by TEXT,
              consumed_at TEXT,
              consumed_by TEXT
            );

            CREATE TRIGGER IF NOT EXISTS runtime_syntax_approvals_bindings_immutable
            BEFORE UPDATE OF execution_request_id, capability, requester_principal
            ON runtime_syntax_approvals
            WHEN OLD.decision = 'approved'
             AND (
               OLD.execution_request_id IS NOT NEW.execution_request_id
               OR OLD.capability IS NOT NEW.capability
               OR OLD.requester_principal IS NOT NEW.requester_principal
             )
            BEGIN
              SELECT RAISE(ABORT, 'Approved runtime syntax approval bindings are immutable');
            END;

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

    # --- internal runtime.syntax approvals -----------------------------------

    @staticmethod
    def _approval_time(value: datetime | None = None) -> str:
        timestamp = value or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("Approval timestamps must be timezone-aware")
        return timestamp.astimezone(timezone.utc).isoformat()

    def create_runtime_syntax_approval(
        self,
        *,
        requester_principal: str,
        expires_at: datetime,
        created_at: datetime | None = None,
    ) -> str:
        """Create a server-issued, pending approval for one syntax execution."""
        principal = requester_principal.strip()
        if not principal:
            raise ValueError("requester_principal is required")
        execution_request_id = uuid4().hex
        self._conn.execute(
            """
            INSERT INTO runtime_syntax_approvals (
              execution_request_id, capability, requester_principal, decision,
              created_at, expires_at
            ) VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (
                execution_request_id,
                RUNTIME_SYNTAX_CAPABILITY,
                principal,
                self._approval_time(created_at),
                self._approval_time(expires_at),
            ),
        )
        self._conn.commit()
        return execution_request_id

    def decide_runtime_syntax_approval(
        self,
        execution_request_id: str,
        *,
        approved: bool,
        decided_by: str,
        now: datetime | None = None,
    ) -> bool:
        """Record one owner decision only while the pending record is unexpired."""
        owner = decided_by.strip()
        if not owner:
            raise ValueError("decided_by is required")
        try:
            if now is None:
                if self.backend == "postgres":
                    timestamp_sql = "CURRENT_TIMESTAMP::text"
                    expiry_sql = "expires_at::timestamptz > CURRENT_TIMESTAMP"
                else:
                    timestamp_sql = "strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')"
                    expiry_sql = "julianday(expires_at) > julianday('now')"
                params = (
                    "approved" if approved else "denied",
                    owner,
                    execution_request_id,
                    RUNTIME_SYNTAX_CAPABILITY,
                )
            else:
                decided_at = self._approval_time(now)
                timestamp_sql = "?"
                expiry_sql = "expires_at > ?"
                params = (
                    "approved" if approved else "denied",
                    decided_at,
                    owner,
                    execution_request_id,
                    RUNTIME_SYNTAX_CAPABILITY,
                    decided_at,
                )
            cursor = self._conn.execute(
                f"""
                UPDATE runtime_syntax_approvals
                SET decision = ?, decided_at = {timestamp_sql}, decided_by = ?
                WHERE execution_request_id = ?
                  AND capability = ?
                  AND decision = 'pending'
                  AND {expiry_sql}
                """,
                params,
            )
            self._conn.commit()
            return cursor.rowcount == 1
        except Exception:
            self._conn.rollback()
            raise

    def claim_runtime_syntax_approval(
        self,
        execution_request_id: str,
        *,
        capability: str,
        requester_principal: str,
        now: datetime | None = None,
    ) -> RuntimeSyntaxApprovalClaim:
        """Atomically spend one approved record before a later launch.

        A committed claim is intentionally irreversible: callers must not retry
        the capability if a subsequent launch fails.
        """
        principal = requester_principal.strip()
        if not principal:
            raise ValueError("requester_principal is required")
        try:
            if now is None:
                if self.backend == "postgres":
                    timestamp_sql = "CURRENT_TIMESTAMP::text"
                    expiry_sql = "expires_at::timestamptz > CURRENT_TIMESTAMP"
                else:
                    timestamp_sql = "strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')"
                    expiry_sql = "julianday(expires_at) > julianday('now')"
                params = (
                    principal,
                    execution_request_id,
                    capability,
                    principal,
                )
            else:
                claimed_at = self._approval_time(now)
                timestamp_sql = "?"
                expiry_sql = "expires_at > ?"
                params = (
                    claimed_at,
                    principal,
                    execution_request_id,
                    capability,
                    principal,
                    claimed_at,
                )
            cursor = self._conn.execute(
                f"""
                UPDATE runtime_syntax_approvals
                SET consumed_at = {timestamp_sql}, consumed_by = ?
                WHERE execution_request_id = ?
                  AND capability = ?
                  AND requester_principal = ?
                  AND decision = 'approved'
                  AND {expiry_sql}
                  AND consumed_at IS NULL
                """,
                params,
            )
            self._conn.commit()
            if cursor.rowcount == 1:
                return RuntimeSyntaxApprovalClaim(claimed=True, reason="claimed")
            return RuntimeSyntaxApprovalClaim(claimed=False, reason="denied")
        except Exception:
            try:
                self._conn.rollback()
            except Exception:
                pass
            logger.warning("Runtime syntax approval storage unavailable")
            return RuntimeSyntaxApprovalClaim(claimed=False, reason="storage_unavailable")

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

    def list_audit(self, *, limit: int = 100, request_id: str | None = None) -> list[dict[str, Any]]:
        where = ""
        params: tuple = (limit,)
        if request_id is not None:
            field = "detail_json::jsonb ->> 'request_id'" if self.backend == "postgres" else "json_extract(detail_json, '$.request_id')"
            where = f"WHERE module = ? AND ({field}) = ?"
            params = ("capabilities", request_id, limit)
        cur = self._conn.execute(
            f"""
            SELECT * FROM audit_events
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
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

    def update_lead_conversion(self, lead_id: str, conversion_outcome: str) -> None:
        """Record a conversion outcome without rewriting the rest of the lead."""
        self._conn.execute(
            """
            UPDATE leads
            SET conversion_outcome = ?
            WHERE lead_id = ?
              AND conversion_outcome IN ('uncontacted', '', 'none')
            """,
            (conversion_outcome, lead_id),
        )
        self._conn.commit()

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
