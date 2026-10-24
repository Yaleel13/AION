"""Local-first durable conversation memory for AION OS.

This module mirrors the small conversation-memory contract used by the Next.js
chat route, but stores data in the durable local ``sessions.db`` SQLite file.
It requires no API key or owner token and is exposed only through the
loopback-only FastAPI endpoint in ``aion.main`` when ``AION_RUNTIME_MODE=local``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from aion.durable.paths import resolve_durable_paths


class LocalMemoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=100_000)


class LocalMemoryRequest(BaseModel):
    action: Literal["load", "append", "search", "remember", "forget", "replace", "facts"]
    client_session_id: str = Field(min_length=16, max_length=200)
    messages: list[LocalMemoryMessage] = Field(default_factory=list, max_length=4)
    previous_response_id: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    runtime: str | None = Field(default=None, max_length=200)
    query: str | None = Field(default=None, max_length=2_000)
    content: str | None = Field(default=None, max_length=10_000)
    replacement: str | None = Field(default=None, max_length=10_000)
    category: str | None = Field(default=None, max_length=100)
    source_message_content: str | None = Field(default=None, max_length=100_000)
    include_inactive: bool = False
    limit: int = Field(default=6, ge=1, le=50)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_memory_path() -> Path:
    return resolve_durable_paths().session_db


def _connect() -> sqlite3.Connection:
    path = local_memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS local_conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          client_session_id TEXT NOT NULL UNIQUE,
          previous_response_id TEXT,
          model TEXT,
          runtime TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS local_conversation_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id INTEGER NOT NULL,
          role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
          content TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY (conversation_id) REFERENCES local_conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS local_conversation_messages_conversation_idx
          ON local_conversation_messages(conversation_id, id);

        CREATE TABLE IF NOT EXISTS local_memory_facts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          content TEXT NOT NULL,
          category TEXT,
          status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'forgotten', 'superseded')),
          superseded_by INTEGER,
          source_conversation_id INTEGER,
          source_message_id INTEGER,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY (superseded_by) REFERENCES local_memory_facts(id),
          FOREIGN KEY (source_conversation_id) REFERENCES local_conversations(id) ON DELETE SET NULL,
          FOREIGN KEY (source_message_id) REFERENCES local_conversation_messages(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS local_memory_facts_status_idx
          ON local_memory_facts(status, updated_at);
        """
    )
    return conn


def _conversation_id(conn: sqlite3.Connection, client_session_id: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM local_conversations WHERE client_session_id = ?",
        (client_session_id,),
    ).fetchone()
    return int(row["id"]) if row else None


def _ensure_conversation(conn: sqlite3.Connection, client_session_id: str) -> int:
    existing = _conversation_id(conn, client_session_id)
    now = _now()
    if existing is not None:
        conn.execute(
            "UPDATE local_conversations SET updated_at = ? WHERE id = ?",
            (now, existing),
        )
        return existing
    cursor = conn.execute(
        "INSERT INTO local_conversations (client_session_id, created_at, updated_at) VALUES (?, ?, ?)",
        (client_session_id, now, now),
    )
    return int(cursor.lastrowid)


def _ensure_source_message(
    conn: sqlite3.Connection,
    conversation_id: int,
    source_content: str | None,
) -> int | None:
    content = (source_content or "").strip()
    if not content:
        return None
    existing = conn.execute(
        """SELECT id FROM local_conversation_messages
        WHERE conversation_id = ? AND role = 'user' AND content = ?
        ORDER BY id DESC LIMIT 1""",
        (conversation_id, content),
    ).fetchone()
    if existing:
        return int(existing["id"])
    cursor = conn.execute(
        """INSERT INTO local_conversation_messages
        (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)""",
        (conversation_id, content, _now()),
    )
    return int(cursor.lastrowid)


def _fact_payload(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "content": row["content"],
        "category": row["category"],
        "status": row["status"],
        "superseded_by": row["superseded_by"],
        "source_conversation_id": row["source_conversation_id"],
        "source_message_id": row["source_message_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def handle_local_memory(body: LocalMemoryRequest) -> dict:
    """Execute one local memory operation against durable SQLite."""
    conn = _connect()
    try:
        if body.action == "load":
            conversation = conn.execute(
                """SELECT id, previous_response_id, model, runtime
                FROM local_conversations WHERE client_session_id = ?""",
                (body.client_session_id,),
            ).fetchone()
            if not conversation:
                return {"found": False, "messages": [], "previous_response_id": None}
            rows = conn.execute(
                """SELECT role, content FROM local_conversation_messages
                WHERE conversation_id = ? ORDER BY id DESC LIMIT 50""",
                (conversation["id"],),
            ).fetchall()
            return {
                "found": True,
                "messages": [
                    {"role": row["role"], "content": row["content"]}
                    for row in reversed(rows)
                    if row["role"] in {"user", "assistant"}
                ],
                "previous_response_id": conversation["previous_response_id"],
                "model": conversation["model"],
                "runtime": conversation["runtime"],
            }

        if body.action == "search":
            query = (body.query or "").strip().lower()
            if not query:
                return {"facts": [], "history": []}
            pattern = f"%{query}%"
            current_conversation_id = _conversation_id(conn, body.client_session_id)
            facts = conn.execute(
                """SELECT id, content, category FROM local_memory_facts
                WHERE status = 'active' AND lower(content) LIKE ?
                ORDER BY updated_at DESC, id DESC LIMIT ?""",
                (pattern, min(body.limit, 8)),
            ).fetchall()
            if current_conversation_id is None:
                history = conn.execute(
                    """SELECT id, content FROM local_conversation_messages
                    WHERE role = 'user' AND lower(content) LIKE ?
                    ORDER BY id DESC LIMIT ?""",
                    (pattern, min(body.limit, 8)),
                ).fetchall()
            else:
                history = conn.execute(
                    """SELECT id, content FROM local_conversation_messages
                    WHERE role = 'user' AND lower(content) LIKE ? AND conversation_id <> ?
                    ORDER BY id DESC LIMIT ?""",
                    (pattern, current_conversation_id, min(body.limit, 8)),
                ).fetchall()
            return {
                "facts": [
                    {"id": row["id"], "content": row["content"], "category": row["category"], "score": 1.0}
                    for row in facts
                ],
                "history": [
                    {"id": row["id"], "content": row["content"], "score": 1.0}
                    for row in history
                ],
            }

        if body.action == "facts":
            if body.include_inactive:
                rows = conn.execute(
                    "SELECT * FROM local_memory_facts ORDER BY updated_at DESC, id DESC LIMIT ?",
                    (body.limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM local_memory_facts WHERE status = 'active'
                    ORDER BY updated_at DESC, id DESC LIMIT ?""",
                    (body.limit,),
                ).fetchall()
            return {"facts": [_fact_payload(row) for row in rows]}

        if body.action == "remember":
            content = (body.content or "").strip()
            if not content:
                raise ValueError("Memory content is required")
            conversation_id = _ensure_conversation(conn, body.client_session_id)
            source_message_id = _ensure_source_message(
                conn, conversation_id, body.source_message_content
            )
            existing = conn.execute(
                """SELECT id FROM local_memory_facts
                WHERE status = 'active' AND lower(trim(content)) = lower(trim(?))
                ORDER BY updated_at DESC LIMIT 1""",
                (content,),
            ).fetchone()
            now = _now()
            if existing:
                conn.execute(
                    """UPDATE local_memory_facts SET category = COALESCE(?, category),
                    source_conversation_id = COALESCE(source_conversation_id, ?),
                    source_message_id = COALESCE(source_message_id, ?), updated_at = ?
                    WHERE id = ?""",
                    ((body.category or "").strip() or None, conversation_id, source_message_id, now, existing["id"]),
                )
                conn.commit()
                return {"remembered": True, "id": existing["id"], "deduplicated": True}
            cursor = conn.execute(
                """INSERT INTO local_memory_facts
                (content, category, source_conversation_id, source_message_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (content, (body.category or "").strip() or None, conversation_id, source_message_id, now, now),
            )
            conn.commit()
            return {"remembered": True, "id": cursor.lastrowid, "deduplicated": False}

        if body.action == "replace":
            old_content = (body.content or "").strip()
            new_content = (body.replacement or "").strip()
            if not old_content or not new_content:
                raise ValueError("Exact old and replacement memory content are required")
            old = conn.execute(
                """SELECT id, category FROM local_memory_facts
                WHERE status = 'active' AND lower(trim(content)) = lower(trim(?))
                ORDER BY updated_at DESC LIMIT 1""",
                (old_content,),
            ).fetchone()
            if not old:
                return {"replaced": False, "exact_match": False}
            duplicate = conn.execute(
                """SELECT id FROM local_memory_facts
                WHERE status = 'active' AND lower(trim(content)) = lower(trim(?)) AND id <> ?
                ORDER BY updated_at DESC LIMIT 1""",
                (new_content, old["id"]),
            ).fetchone()
            now = _now()
            if duplicate:
                new_id = int(duplicate["id"])
            else:
                conversation_id = _ensure_conversation(conn, body.client_session_id)
                source_message_id = _ensure_source_message(
                    conn, conversation_id, body.source_message_content
                )
                cursor = conn.execute(
                    """INSERT INTO local_memory_facts
                    (content, category, source_conversation_id, source_message_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        new_content,
                        (body.category or "").strip() or old["category"],
                        conversation_id,
                        source_message_id,
                        now,
                        now,
                    ),
                )
                new_id = int(cursor.lastrowid)
            conn.execute(
                """UPDATE local_memory_facts SET status = 'superseded',
                superseded_by = ?, updated_at = ? WHERE id = ?""",
                (new_id, now, old["id"]),
            )
            conn.commit()
            return {"replaced": True, "exact_match": True, "old_id": old["id"], "new_id": new_id}

        if body.action == "forget":
            content = (body.content or body.query or "").strip()
            if not content:
                raise ValueError("Exact memory content is required")
            cursor = conn.execute(
                """UPDATE local_memory_facts SET status = 'forgotten', updated_at = ?
                WHERE status = 'active' AND lower(trim(content)) = lower(trim(?))""",
                (_now(), content),
            )
            conn.commit()
            return {"forgotten": cursor.rowcount, "exact_match": cursor.rowcount > 0}

        conversation_id = _ensure_conversation(conn, body.client_session_id)
        conn.execute(
            """UPDATE local_conversations SET
            previous_response_id = COALESCE(?, previous_response_id),
            model = COALESCE(?, model), runtime = COALESCE(?, runtime), updated_at = ?
            WHERE id = ?""",
            (body.previous_response_id, body.model, body.runtime, _now(), conversation_id),
        )
        inserted = 0
        for message in body.messages:
            last = conn.execute(
                """SELECT role, content FROM local_conversation_messages
                WHERE conversation_id = ? ORDER BY id DESC LIMIT 1""",
                (conversation_id,),
            ).fetchone()
            if last and last["role"] == message.role and last["content"] == message.content:
                continue
            conn.execute(
                """INSERT INTO local_conversation_messages
                (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)""",
                (conversation_id, message.role, message.content, _now()),
            )
            inserted += 1
        conn.commit()
        return {"saved": True, "message_count": inserted}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
