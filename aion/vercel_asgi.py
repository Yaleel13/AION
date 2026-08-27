"""ASGI adapter for serving the existing FastAPI app under Vercel /api paths."""

from __future__ import annotations

from aion.main import app as runtime_app


class StripApiPrefix:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        if path == "/api":
            mapped = "/"
        elif path.startswith("/api/"):
            mapped = path[4:]
        else:
            mapped = path

        forwarded = dict(scope)
        forwarded["path"] = mapped
        forwarded["raw_path"] = mapped.encode("utf-8")
        await self.app(forwarded, receive, send)


app = StripApiPrefix(runtime_app)
