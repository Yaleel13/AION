"""Owner-only capability permission registry endpoint."""
from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Header, HTTPException

from aion.capabilities import capability_registry

app = FastAPI()


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/internal/capabilities")
async def get_capabilities(authorization: str | None = Header(default=None)) -> dict:
    _require_owner(authorization)
    return capability_registry()
