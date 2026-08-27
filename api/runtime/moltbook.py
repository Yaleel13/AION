"""Sanitized read-only Moltbook health probe for production acceptance.

This endpoint never returns credentials or Moltbook content. It performs only
GET operations through the Phase 1 read-only client and reports booleans/counts
needed to verify live connectivity.
"""

from __future__ import annotations

import os

from fastapi import FastAPI

from aion.moltbook.client import create_client
from aion.moltbook.settings import load_moltbook_settings

app = FastAPI()


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@app.get("/api/runtime/moltbook")
async def moltbook_health() -> dict:
    settings = load_moltbook_settings()
    client = create_client(settings)

    profile_ok = False
    feed_ok = False
    feed_items = 0
    error_kind: str | None = None

    try:
        profile = await client.profile()
        profile_ok = isinstance(profile, dict)

        feed = await client.feed(sort="new", limit=3)
        feed_ok = isinstance(feed, dict)
        items = feed.get("posts") or feed.get("data") or []
        if isinstance(items, list):
            feed_items = len(items)
    except Exception as exc:  # noqa: BLE001 - health probe returns sanitized class only
        error_kind = type(exc).__name__

    execute_enabled = _flag("MOLTBOOK_PHASE2_EXECUTE", False)
    autonomy_enabled = _flag("MOLTBOOK_CONTROLLED_AUTONOMY", False)
    dry_run = _flag("MOLTBOOK_AUTONOMY_DRY_RUN", True)

    return {
        "ok": profile_ok and feed_ok,
        "mode": settings.mode,
        "api_key_present": bool(settings.api_key),
        "profile_read_ok": profile_ok,
        "feed_read_ok": feed_ok,
        "feed_items_observed": feed_items,
        "outbound_enabled": settings.outbound_enabled,
        "execute_enabled": execute_enabled,
        "autonomy_enabled": autonomy_enabled,
        "dry_run": dry_run,
        "live_writes_enabled": bool(
            settings.outbound_enabled and execute_enabled and autonomy_enabled and not dry_run
        ),
        "error_kind": error_kind,
        "content_exposed": False,
    }
