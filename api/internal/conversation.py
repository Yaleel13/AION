"""Owner-protected serverless conversation memory endpoint for AION.

This endpoint is called only by AION's server-side Next.js routes. It never
accepts browser credentials directly and never exposes the database URL.
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
    action: Literal["load", "append"]
    client_session_id: str = Field(min_length=16, max_length=200)
    messages: list[MemoryMessage] = Field(default_factory=list, max_length=4)
    previous_response_id: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    runtime: str | None = Field(default=None, max_length=200)


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


@app.post("/api/internal/conversation")
async def conversation_memory(
    body: MemoryRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_auth(authorization)
    _require_postgres()

    conn = connect_postgres()
    try:
        if body.action == "load":
            conversation = conn.execute(
                """
                SELECT id, previous_response_id, model, runtime, created_at, updated_at
                FROM aion.conversations
                WHERE client_session_id = ?
                """,
                (body.client_session_id,),
            ).fetchone()
            if not conversation:
                return {"found": False, "messages": [], "previous_response_id": None}

            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM aion.conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 50
                """,
                (conversation["id"],),
            ).fetchall()
            messages = [
                {"role": row["role"], "content": row["content"]}
                for row in reversed(rows)
                if row["role"] in {"user", "assistant"}
            ]
            return {
                "found": True,
                "messages": messages,
                "previous_response_id": conversation["previous_response_id"],
                "model": conversation["model"],
                "runtime": conversation["runtime"],
            }

        conversation = conn.execute(
            """
            INSERT INTO aion.conversations (
                client_session_id, previous_response_id, model, runtime, updated_at
            )
            VALUES (?, ?, ?, ?, now())
            ON CONFLICT (client_session_id)
            DO UPDATE SET
                previous_response_id = COALESCE(EXCLUDED.previous_response_id, aion.conversations.previous_response_id),
                model = COALESCE(EXCLUDED.model, aion.conversations.model),
                runtime = COALESCE(EXCLUDED.runtime, aion.conversations.runtime),
                updated_at = now()
            RETURNING id
            """,
            (
                body.client_session_id,
                body.previous_response_id,
                body.model,
                body.runtime,
            ),
        ).fetchone()

        for message in body.messages:
            conn.execute(
                """
                INSERT INTO aion.conversation_messages (conversation_id, role, content)
                VALUES (?, ?, ?)
                """,
                (conversation["id"], message.role, message.content),
            )
        conn.commit()
        return {"saved": True, "message_count": len(body.messages)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        raise HTTPException(status_code=500, detail="Conversation memory operation failed") from exc
    finally:
        conn.close()
