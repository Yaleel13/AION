"""Structured outbound / go-live gate status (no secrets)."""

from __future__ import annotations

import os
from typing import Any

from aion.moltbook.errors import MoltbookConfigError
from aion.moltbook.security import KillSwitch
from aion.moltbook.settings import load_moltbook_settings, observe_moltbook_env
from aion.runtime_status import build_runtime_status


def build_outbound_gate_status() -> dict[str, Any]:
    """Return outbound blockers plus the owner go-live checklist."""
    kill = KillSwitch.from_env()
    observed = observe_moltbook_env()
    try:
        settings = load_moltbook_settings()
        moltbook_ok = True
        moltbook_error = None
    except MoltbookConfigError as exc:
        settings = None
        moltbook_ok = False
        moltbook_error = str(exc)

    blockers: list[str] = []
    actions: list[str] = []

    if kill.engaged:
        blockers.append("Kill switch is engaged (AION_KILL_SWITCH=true)")
        actions.append("Set AION_KILL_SWITCH=false in Vercel project env to re-enable operations.")

    if not moltbook_ok:
        blockers.append(f"Moltbook config error: {moltbook_error}")
        if observed.execute_enabled and not observed.outbound_enabled:
            actions.append(
                "Set MOLTBOOK_OUTBOUND_ENABLED=true in Vercel Production. "
                "MOLTBOOK_EXECUTE_ENABLED is already true; both are required or Moltbook fails closed."
            )
        else:
            actions.append("Check MOLTBOOK_MODE, MOLTBOOK_API_KEY, MOLTBOOK_BASE_URL in Vercel env.")
    elif settings is not None:
        if settings.mode == "mock":
            blockers.append("MOLTBOOK_MODE=mock — live Moltbook access disabled")
            actions.append("Set MOLTBOOK_MODE=live in Vercel project env.")
        if not settings.api_key:
            blockers.append("MOLTBOOK_API_KEY is not set")
            actions.append("Set MOLTBOOK_API_KEY to your Moltbook agent API key in Vercel env.")
        if not settings.outbound_enabled:
            blockers.append("MOLTBOOK_OUTBOUND_ENABLED=false")
            actions.append("Set MOLTBOOK_OUTBOUND_ENABLED=true in Vercel project env (requires MOLTBOOK_MODE=live + API key).")
        if not settings.execute_enabled:
            blockers.append("MOLTBOOK_EXECUTE_ENABLED=false")
            actions.append("Set MOLTBOOK_EXECUTE_ENABLED=true in Vercel project env (requires outbound_enabled=true).")

    runtime = build_runtime_status()
    payment_rails = runtime.get("payment_rails") or {}
    operations = runtime.get("operations") or {}
    stripe_ready = bool(payment_rails.get("stripe_ready_for_checkout", False))
    if not stripe_ready:
        blockers.append("Stripe checkout is not fully configured")
        actions.append("Set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and STRIPE_CHECKOUT_ENABLED=true in Vercel env.")

    database_ok = bool(operations.get("database_url_configured"))
    owner_token_ok = bool(operations.get("owner_token_configured"))
    cron_ok = bool(operations.get("cron_secret_configured"))
    fulfillment_enabled = (os.getenv("FULFILLMENT_CRON_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not database_ok:
        actions.append("Set AION_DATABASE_URL to the dedicated AION Supabase pooler URL.")
    if not owner_token_ok:
        actions.append("Set AION_OWNER_TOKEN so Boardroom and owner APIs can authenticate.")
    if not cron_ok:
        actions.append("Set CRON_SECRET so Vercel Cron can run revenue-ops and fulfillment.")
    if not fulfillment_enabled:
        actions.append(
            "After a paid test order succeeds, set FULFILLMENT_CRON_ENABLED=true to auto-fulfill paid orders."
        )

    go_live_checklist = [
        {
            "id": "kill_switch",
            "ok": not kill.engaged,
            "label": "Kill switch disengaged",
            "action": "Keep AION_KILL_SWITCH=false unless you need an emergency stop.",
        },
        {
            "id": "postgres",
            "ok": database_ok,
            "label": "Durable Postgres",
            "action": "Set AION_DATABASE_URL (aion_app pooler URI for gtviwpevltuqhygsbsou).",
        },
        {
            "id": "owner_token",
            "ok": owner_token_ok,
            "label": "Owner token",
            "action": "Set AION_OWNER_TOKEN in Vercel project env.",
        },
        {
            "id": "cron_secret",
            "ok": cron_ok,
            "label": "Cron secret",
            "action": "Set CRON_SECRET to match the Vercel Cron Authorization bearer.",
        },
        {
            "id": "stripe",
            "ok": stripe_ready,
            "label": "Stripe checkout",
            "action": "Set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_CHECKOUT_ENABLED=true.",
        },
        {
            "id": "moltbook_live",
            "ok": observed.mode == "live" and observed.api_key_present,
            "label": "Moltbook live + API key",
            "action": "Set MOLTBOOK_MODE=live and MOLTBOOK_API_KEY.",
        },
        {
            "id": "outbound",
            "ok": bool(settings and settings.outbound_enabled and settings.execute_enabled),
            "label": "Moltbook outbound + execute",
            "action": "Set MOLTBOOK_OUTBOUND_ENABLED=true and MOLTBOOK_EXECUTE_ENABLED=true after reviewing drafts.",
        },
        {
            "id": "fulfillment",
            "ok": fulfillment_enabled,
            "label": "Fulfillment cron",
            "action": "Set FULFILLMENT_CRON_ENABLED=true after a successful paid test order.",
        },
    ]
    ready_for_revenue = all(
        item["ok"]
        for item in go_live_checklist
        if item["id"] in {"kill_switch", "postgres", "owner_token", "cron_secret", "stripe"}
    )

    current_mode = "inactive"
    if not blockers:
        current_mode = "live_outbound_ready"
    elif kill.engaged:
        current_mode = "kill_switch_engaged"
    elif settings and settings.outbound_enabled and settings.execute_enabled:
        current_mode = "partial"

    return {
        "current_mode": current_mode,
        "kill_switch_engaged": kill.engaged,
        "moltbook_mode": settings.mode if settings else observed.mode,
        "moltbook_api_key_set": bool(settings.api_key) if settings else observed.api_key_present,
        "moltbook_outbound_enabled": (
            settings.outbound_enabled if settings else observed.outbound_enabled
        ),
        "moltbook_execute_enabled": (
            settings.execute_enabled if settings else observed.execute_enabled
        ),
        "moltbook_error": moltbook_error,
        "stripe_checkout_ready": stripe_ready,
        "ready_for_revenue": ready_for_revenue,
        "go_live_checklist": go_live_checklist,
        "blockers": blockers,
        "owner_actions": actions,
        "ready_for_live_outbound": len(blockers) == 0,
    }
