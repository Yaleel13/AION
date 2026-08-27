"""Truthful runtime status payload for UI and ops (no secrets)."""

from __future__ import annotations

import os
from typing import Any

from aion import config
from aion.durable.db import storage_status
from aion.moltbook.autonomy_policy import AutonomyMode, AutonomyPolicy
from aion.moltbook.errors import MoltbookConfigError
from aion.moltbook.security import KillSwitch
from aion.moltbook.settings import load_moltbook_settings


def build_runtime_status() -> dict[str, Any]:
    """Assemble a non-secret snapshot of real runtime gates and backends."""
    storage = storage_status().as_dict()

    try:
        moltbook_settings = load_moltbook_settings()
        moltbook = {
            "configured": moltbook_settings.is_mock or moltbook_settings.configured_for_live,
            "mode": moltbook_settings.mode,
            "api_key_present": bool(moltbook_settings.api_key),
            "outbound_enabled": False,
            "execute_enabled": False,
            "phase": "phase2-controlled-growth",
        }
    except MoltbookConfigError as exc:
        moltbook = {
            "configured": False,
            "mode": None,
            "api_key_present": False,
            "outbound_enabled": False,
            "execute_enabled": False,
            "phase": "phase2-controlled-growth",
            "error": str(exc),
        }

    policy = AutonomyPolicy.from_env()
    dry_run_raw = (os.getenv("MOLTBOOK_AUTONOMY_DRY_RUN") or "true").strip().lower()
    dry_run = dry_run_raw not in {"0", "false", "no", "off"}
    kill = KillSwitch.from_env()
    paper_mode = (os.getenv("AION_PAPER_PRICE_MODE") or "live_public").strip() or "live_public"

    live_writes = bool(
        policy.mode is AutonomyMode.ACTIVE
        and policy.experiment_active()
        and not dry_run
        and not kill.engaged
    )

    vercel_runtime = bool(os.getenv("VERCEL"))

    return {
        "ok": True,
        "source": "runtime_status",
        "fixture": False,
        "storage": storage,
        "moltbook": moltbook,
        "autonomy": {
            "mode": policy.mode.value,
            "dry_run": dry_run,
            "live_writes_enabled": live_writes,
            "experiment_active": policy.experiment_active(),
            "default": "inactive",
        },
        "kill_switch": kill.snapshot(),
        "paper_market_data": {
            "price_mode": paper_mode,
            "live_trading": False,
            "note": "Paper trading only. Official metrics separate live public market marks from mock/fallback prices.",
        },
        "providers": {
            "openai_configured": bool(config.OPENAI_API_KEY),
            "gemini_configured": bool(config.GEMINI_API_KEY),
            "vercel_ai_gateway_fallback_eligible": vercel_runtime,
        },
        "operations": {
            "database_url_configured": bool(os.getenv("AION_DATABASE_URL")),
            "owner_token_configured": bool(os.getenv("AION_OWNER_TOKEN")),
            "cron_secret_configured": bool(os.getenv("CRON_SECRET")),
            "terminal_executor_connected": False,
        },
        "safety": {
            "moltbook_outbound_default": False,
            "autonomy_default": "inactive",
            "autonomy_dry_run_default": True,
            "paper_is_not_live_trading": True,
        },
    }
