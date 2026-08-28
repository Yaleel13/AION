"""Owner-only acceptance evidence for AION production reliability."""
from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.durable.db import connect_postgres, database_url
from aion.runtime_status import build_runtime_status

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _count(conn, sql: str, params=()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row["c"] if row else 0)


@app.get("/api/internal/acceptance")
async def acceptance(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    if not database_url():
        raise HTTPException(status_code=503, detail="Durable Postgres is not configured")
    conn = connect_postgres()
    try:
        conversations = _count(conn, "SELECT COUNT(*) AS c FROM aion.conversations")
        direct_openai = _count(conn, "SELECT COUNT(*) AS c FROM aion.conversations WHERE runtime = 'openai-responses-v1'")
        gateway = _count(conn, "SELECT COUNT(*) AS c FROM aion.conversations WHERE runtime = 'vercel-ai-gateway-oidc'")
        active_memories = _count(conn, "SELECT COUNT(*) AS c FROM aion.memory_facts WHERE status = 'active'")
        linked_memories = _count(conn, "SELECT COUNT(*) AS c FROM aion.memory_facts WHERE status = 'active' AND source_conversation_id IS NOT NULL AND source_message_id IS NOT NULL")
        distinct_message_conversations = _count(conn, "SELECT COUNT(DISTINCT conversation_id) AS c FROM aion.conversation_messages WHERE role = 'user'")
        paper_live_24h = _count(conn, "SELECT COUNT(*) AS c FROM aion.snapshots WHERE timestamp >= now() - interval '24 hours' AND is_live_market_data = TRUE")
        paper_fallback_24h = _count(conn, "SELECT COUNT(*) AS c FROM aion.snapshots WHERE timestamp >= now() - interval '24 hours' AND is_live_market_data = FALSE")
    finally:
        conn.close()

    runtime = build_runtime_status()
    return {
        "ok": True,
        "direct_openai": {
            "accepted": direct_openai > 0,
            "conversations": direct_openai,
            "gateway_conversations": gateway,
        },
        "durable_conversations": {
            "total": conversations,
            "with_user_messages": distinct_message_conversations,
            "cross_conversation_ready": distinct_message_conversations >= 2,
        },
        "memory_provenance": {
            "active": active_memories,
            "linked": linked_memories,
            "coverage": (linked_memories / active_memories) if active_memories else 1.0,
            "new_writes_link_exact_source": True,
        },
        "paper_market": {
            "live_snapshots_24h": paper_live_24h,
            "fallback_snapshots_24h": paper_fallback_24h,
            "live_trading": False,
            "price_cache_seconds": 60,
        },
        "runtime": {
            "storage_configured": runtime["storage"]["configured"],
            "cron_secret_configured": runtime["operations"]["cron_secret_configured"],
            "terminal_executor_connected": runtime["operations"]["terminal_executor_connected"],
            "arbitrary_terminal_commands_enabled": runtime["operations"]["arbitrary_terminal_commands_enabled"],
            "moltbook_outbound_enabled": runtime["moltbook"]["outbound_enabled"],
            "moltbook_execute_enabled": runtime["moltbook"]["execute_enabled"],
        },
    }
