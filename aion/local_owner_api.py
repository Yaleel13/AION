"""Reuse the owner serverless handlers on the explicitly local runtime."""

from __future__ import annotations

import importlib
import hmac
import os

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse

from aion.local_memory import LocalMemoryRequest, handle_local_memory

# Fixed surface only. Each handler retains its existing bearer-token policy,
# approval requirements, and execution gates.
OWNER_APIS = (
    "acceptance", "capabilities", "operator-briefing", "outbound-gates",
    "sales-alerts", "moltbook-research", "moltbook-preparation",
    "moltbook-reviews", "moltbook-approvals", "commercial-execution",
)
OWNER_METHODS = {
    name: {"GET"} if name in {"acceptance", "capabilities", "operator-briefing"} else {"GET", "POST"}
    for name in OWNER_APIS
}


class LocalOwnerErrorBoundary:
    """Keep unexpected internal failures structured without exposing diagnostics."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/internal/"):
            await self.app(scope, receive, send)
            return
        started = False

        async def track_start(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, track_start)
        except Exception:
            if started:
                raise
            response = JSONResponse(
                {"detail": "Local owner service is temporarily unavailable."},
                status_code=500, headers={"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)


async def require_local_owner_runtime(request: Request) -> None:
    if (os.getenv("AION_RUNTIME_MODE") or "").strip().lower() != "local":
        raise HTTPException(status_code=503, detail="Local owner runtime is not enabled")
    host = request.client.host if request.client else None
    if host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="Local owner runtime is loopback-only")
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not hmac.compare_digest(
        request.headers.get("authorization", "").encode("utf-8"), f"Bearer {token}".encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def local_owner_conversation(body: LocalMemoryRequest) -> dict:
    """Authenticated internal alias for the existing local memory service."""
    return handle_local_memory(body)


def register_local_owner_api(app: FastAPI) -> None:
    router = APIRouter()
    for name in OWNER_APIS:
        module = importlib.import_module(f"api.internal.{name}")
        # FastAPI sub-apps also contain docs routes; include only their API
        # handlers so the runtime keeps one OpenAPI document and docs surface.
        router.routes.extend(
            route for route in module.app.routes
            if isinstance(route, APIRoute)
            and route.path == f"/api/internal/{name}"
            and route.methods <= OWNER_METHODS[name]
        )
    router.add_api_route("/api/internal/conversation", local_owner_conversation, methods=["POST"])
    app.include_router(router, dependencies=[Depends(require_local_owner_runtime)])
    app.add_middleware(LocalOwnerErrorBoundary)
