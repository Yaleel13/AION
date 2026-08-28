"""Owner-protected serverless conversation and long-term memory endpoint for AION.

This endpoint is called only by AION's server-side Next.js routes. It never
accepts browser credentials directly and never exposes the database URL.
Permanent facts are opt-in: the chat route calls ``remember`` only when the
user explicitly asks AION to remember something.
"""

from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from aion.durable.db import connect_postgres, database_url

app = FastAPI()


class MemoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=100_000)


class MemoryRequest(BaseModel):
    action: Literal["load", "append", "search", "remember", "forget", "replace", "facts"]
    client_session_id: str = Field(min_length=16, max_length=200)
    messages: list[MemoryMessage] = Field(default_factory=list, max_length=4)
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


def _require_internal_auth(authorization: str | None) -> None:
    expected = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="AION_OWNER_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    provided = authorization.removeprefix("Bearer ").strip()
    if provided != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


def _require_postgres() -> None:
    if not database_url():
        raise HTTPException(status_code=503, detail="AION_DATABASE_URL is not configured")


def _conversation_id(conn, client_session_id: str) -> str | None:
    row = conn.execute(
        "SELECT id FROM aion.conversations WHERE client_session_id = ?",
        (client_session_id,),
    ).fetchone()
    return row["id"] if row else None


def _ensure_conversation(conn, client_session_id: str) -> str:
    row = conn.execute(
        """
        INSERT INTO aion.conversations (client_session_id, updated_at)
        VALUES (?, now())
        ON CONFLICT (client_session_id)
        DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        (client_session_id,),
    ).fetchone()
    return str(row["id"])


def _ensure_source_message(conn, conversation_id: str, source_content: str | None) -> int | None:
    content = (source_content or "").strip()
    if not content:
        return None
    existing = conn.execute(
        """
        SELECT id FROM aion.conversation_messages
        WHERE conversation_id = ? AND role = 'user' AND content = ?
        ORDER BY created_at DESC, id DESC LIMIT 1
        """,
        (conversation_id, content),
    ).fetchone()
    if existing:
        return int(existing["id"])
    row = conn.execute(
        """
        INSERT INTO aion.conversation_messages (conversation_id, role, content)
        VALUES (?, 'user', ?)
        RETURNING id
        """,
        (conversation_id, content),
    ).fetchone()
    return int(row["id"])


def _fact_payload(row) -> dict:
    return {
        "id": row["id"],
        "content": row["content"],
        "category": row["category"],
        "status": row["status"],
        "superseded_by": row["superseded_by"],
        "source_conversation_id": str(row["source_conversation_id"]) if row.get("source_conversation_id") else None,
        "source_message_id": row["source_message_id"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


@app.post("/api/internal/conversation")
async def conversation_memory(body: MemoryRequest, authorization: str | None = Header(default=None)) -> dict:
    _require_internal_auth(authorization)
    _require_postgres()
    conn = connect_postgres()
    try:
        if body.action == "load":
            conversation = conn.execute(
                "SELECT id, previous_response_id, model, runtime, created_at, updated_at FROM aion.conversations WHERE client_session_id = ?",
                (body.client_session_id,),
            ).fetchone()
            if not conversation:
                return {"found": False, "messages": [], "previous_response_id": None}
            rows = conn.execute(
                "SELECT role, content, created_at FROM aion.conversation_messages WHERE conversation_id = ? ORDER BY created_at DESC, id DESC LIMIT 50",
                (conversation["id"],),
            ).fetchall()
            return {
                "found": True,
                "messages": [{"role": row["role"], "content": row["content"]} for row in reversed(rows) if row["role"] in {"user", "assistant"}],
                "previous_response_id": conversation["previous_response_id"],
                "model": conversation["model"],
                "runtime": conversation["runtime"],
            }

        if body.action == "search":
            query = (body.query or "").strip()
            if not query:
                return {"facts": [], "history": []}
            current_conversation_id = _conversation_id(conn, body.client_session_id)
            facts = conn.execute(
                """SELECT id, content, category, updated_at, ts_rank_cd(fts, websearch_to_tsquery('english', ?)) AS rank
                FROM aion.memory_facts WHERE status = 'active' AND fts @@ websearch_to_tsquery('english', ?)
                ORDER BY rank DESC, updated_at DESC LIMIT ?""",
                (query, query, min(body.limit, 8)),
            ).fetchall()
            history_params: list[object] = [query, query]
            exclude_clause = ""
            if current_conversation_id:
                exclude_clause = "AND m.conversation_id <> ?"
                history_params.append(current_conversation_id)
            history_params.append(min(body.limit, 8))
            history = conn.execute(
                f"""SELECT m.id, m.content, m.created_at, ts_rank_cd(m.fts, websearch_to_tsquery('english', ?)) AS rank
                FROM aion.conversation_messages m WHERE m.role = 'user'
                AND m.fts @@ websearch_to_tsquery('english', ?) {exclude_clause}
                ORDER BY rank DESC, m.created_at DESC LIMIT ?""",
                tuple(history_params),
            ).fetchall()
            return {
                "facts": [{"id": row["id"], "content": row["content"], "category": row["category"], "score": float(row["rank"] or 0)} for row in facts],
                "history": [{"id": row["id"], "content": row["content"], "score": float(row["rank"] or 0)} for row in history],
            }

        if body.action == "facts":
            where = "" if body.include_inactive else "WHERE status = 'active'"
            rows = conn.execute(
                f"""SELECT id, content, category, status, superseded_by, source_conversation_id, source_message_id, created_at, updated_at
                FROM aion.memory_facts {where} ORDER BY updated_at DESC, id DESC LIMIT ?""",
                (body.limit,),
            ).fetchall()
            return {"facts": [_fact_payload(row) for row in rows]}

        if body.action == "remember":
            content = (body.content or "").strip()
            if not content:
                raise HTTPException(status_code=400, detail="Memory content is required")
            source_conversation_id = _ensure_conversation(conn, body.client_session_id)
            source_message_id = _ensure_source_message(conn, source_conversation_id, body.source_message_content)
            existing = conn.execute(
                "SELECT id FROM aion.memory_facts WHERE status = 'active' AND lower(btrim(content)) = lower(btrim(?)) ORDER BY updated_at DESC LIMIT 1",
                (content,),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE aion.memory_facts SET category = COALESCE(?, category),
                    source_conversation_id = COALESCE(source_conversation_id, ?),
                    source_message_id = COALESCE(source_message_id, ?), updated_at = now() WHERE id = ?""",
                    ((body.category or "").strip() or None, source_conversation_id, source_message_id, existing["id"]),
                )
                conn.commit()
                return {"remembered": True, "id": existing["id"], "deduplicated": True}
            row = conn.execute(
                "INSERT INTO aion.memory_facts (content, category, source_conversation_id, source_message_id) VALUES (?, ?, ?, ?) RETURNING id",
                (content, (body.category or "").strip() or None, source_conversation_id, source_message_id),
            ).fetchone()
            conn.commit()
            return {"remembered": True, "id": row["id"], "deduplicated": False}

        if body.action == "replace":
            old_content = (body.content or "").strip()
            new_content = (body.replacement or "").strip()
            if not old_content or not new_content:
                raise HTTPException(status_code=400, detail="Exact old and replacement memory content are required")
            old = conn.execute(
                "SELECT id, category FROM aion.memory_facts WHERE status = 'active' AND lower(btrim(content)) = lower(btrim(?)) ORDER BY updated_at DESC LIMIT 1",
                (old_content,),
            ).fetchone()
            if not old:
                return {"replaced": False, "exact_match": False}
            duplicate = conn.execute(
                "SELECT id FROM aion.memory_facts WHERE status = 'active' AND lower(btrim(content)) = lower(btrim(?)) AND id <> ? ORDER BY updated_at DESC LIMIT 1",
                (new_content, old["id"]),
            ).fetchone()
            if duplicate:
                new_id = duplicate["id"]
            else:
                source_conversation_id = _ensure_conversation(conn, body.client_session_id)
                source_message_id = _ensure_source_message(conn, source_conversation_id, body.source_message_content)
                inserted = conn.execute(
                    "INSERT INTO aion.memory_facts (content, category, source_conversation_id, source_message_id) VALUES (?, ?, ?, ?) RETURNING id",
                    (new_content, (body.category or "").strip() or old["category"], source_conversation_id, source_message_id),
                ).fetchone()
                new_id = inserted["id"]
            conn.execute("UPDATE aion.memory_facts SET status = 'superseded', superseded_by = ?, updated_at = now() WHERE id = ?", (new_id, old["id"]))
            conn.commit()
            return {"replaced": True, "exact_match": True, "old_id": old["id"], "new_id": new_id}

        if body.action == "forget":
            content = (body.content or body.query or "").strip()
            if not content:
                raise HTTPException(status_code=400, detail="Exact memory content is required")
            rows = conn.execute(
                "UPDATE aion.memory_facts SET status = 'forgotten', updated_at = now() WHERE status = 'active' AND lower(btrim(content)) = lower(btrim(?)) RETURNING id",
                (content,),
            ).fetchall()
            conn.commit()
            return {"forgotten": len(rows), "exact_match": bool(rows)}

        conversation_id = _ensure_conversation(conn, body.client_session_id)
        conn.execute(
            """UPDATE aion.conversations SET previous_response_id = COALESCE(?, previous_response_id),
            model = COALESCE(?, model), runtime = COALESCE(?, runtime), updated_at = now() WHERE id = ?""",
            (body.previous_response_id, body.model, body.runtime, conversation_id),
        )
        inserted = 0
        for message in body.messages:
            last = conn.execute(
                "SELECT role, content FROM aion.conversation_messages WHERE conversation_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
                (conversation_id,),
            ).fetchone()
            if last and last["role"] == message.role and last["content"] == message.content:
                continue
            conn.execute("INSERT INTO aion.conversation_messages (conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id, message.role, message.content))
            inserted += 1
        conn.commit()
        return {"saved": True, "message_count": inserted}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        raise HTTPException(status_code=500, detail="Conversation memory operation failed") from exc
    finally:
        conn.close()
