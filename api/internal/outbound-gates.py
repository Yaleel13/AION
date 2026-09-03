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

from aion.moltbook.security import KillSwitch
from aion.outbound_gates import build_outbound_gate_status

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


class GateToggleRequest(BaseModel):
    outbound_enabled: bool = False
    execute_enabled: bool = False


@app.get("/api/internal/outbound-gates")
async def get_gates(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Return the current outbound gate status and what is blocking it."""
    _require_owner(authorization)
    return {"ok": True, **build_outbound_gate_status()}


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
        **build_outbound_gate_status(),
    }
