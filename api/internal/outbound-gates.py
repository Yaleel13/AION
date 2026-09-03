"""Owner-only outbound-gate status and process-level toggle.

GET  — returns current outbound gate status, what is blocking, and what the owner
        needs to do to enable live outbound.
POST — applies a process-level env var override for the running Vercel function
        invocation ONLY.  This does NOT persist to Vercel project settings.
        Use this for a test activation; set the Vercel env vars permanently for
        durable activation.

The endpoint never enables autonomy beyond what the caller explicitly requests,
never disables the kill switch, and always requires owner authentication.
"""

from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from aion.moltbook.errors import MoltbookConfigError
from aion.moltbook.settings import load_moltbook_settings
from aion.moltbook.security import KillSwitch
from aion.runtime_status import build_runtime_status

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _gate_status() -> dict[str, Any]:
    """Return structured gate status and owner action checklist."""
    kill = KillSwitch.from_env()
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
    stripe_ready = runtime.get("payment_rails", {}).get("stripe_ready_for_checkout", False)
    if not stripe_ready:
        blockers.append("Stripe checkout is not fully configured")
        actions.append("Set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and STRIPE_CHECKOUT_ENABLED=true in Vercel env.")

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
        "moltbook_mode": settings.mode if settings else None,
        "moltbook_api_key_set": bool(settings and settings.api_key),
        "moltbook_outbound_enabled": bool(settings and settings.outbound_enabled),
        "moltbook_execute_enabled": bool(settings and settings.execute_enabled),
        "stripe_checkout_ready": stripe_ready,
        "blockers": blockers,
        "owner_actions": actions,
        "ready_for_live_outbound": len(blockers) == 0,
    }


class GateToggleRequest(BaseModel):
    outbound_enabled: bool = False
    execute_enabled: bool = False


@app.get("/api/internal/outbound-gates")
async def get_gates(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Return the current outbound gate status and what is blocking it."""
    _require_owner(authorization)
    return {"ok": True, **_gate_status()}


@app.post("/api/internal/outbound-gates")
async def set_gates(
    body: GateToggleRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Apply a process-level gate toggle for this invocation only.

    This is not a persistent change.  Use it to test that the activation path
    works before setting permanent env vars in Vercel.  The kill switch, API
    keys, and Stripe config cannot be changed here.
    """
    _require_owner(authorization)

    kill = KillSwitch.from_env()
    if kill.engaged:
        raise HTTPException(status_code=409, detail="Kill switch is engaged; disengage it before toggling outbound gates.")

    if body.outbound_enabled:
        os.environ["MOLTBOOK_OUTBOUND_ENABLED"] = "true"
    else:
        os.environ["MOLTBOOK_OUTBOUND_ENABLED"] = "false"

    if body.execute_enabled and body.outbound_enabled:
        os.environ["MOLTBOOK_EXECUTE_ENABLED"] = "true"
    else:
        os.environ["MOLTBOOK_EXECUTE_ENABLED"] = "false"

    return {
        "ok": True,
        "note": "Process-level only — does not persist across Vercel invocations. Set env vars in Vercel project settings for durable activation.",
        **_gate_status(),
    }
