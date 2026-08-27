"""Async Moltbook API client — Phase 1 read-only surface.

Documented read endpoints used here are sourced from the repository's existing
Moltbook emissary work and the official skill at https://www.moltbook.com/skill.md:

- GET /agents/me
- GET /agents/status
- GET /posts
- GET /posts/{id}
- GET /posts/{id}/comments
- GET /search
- GET /submolts
- GET /submolts/{name}

Write/outbound methods are retained only as disabled stubs that raise
``MoltbookOutboundDisabledError`` and optionally record approval proposals.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from aion.moltbook import mock_data
from aion.moltbook.approval import OutboundAction, OutboundApprovalGate
from aion.moltbook.audit import AuditEvent, AuditLogger
from aion.moltbook.errors import (
    MoltbookConfigError,
    MoltbookError,
    MoltbookOutboundDisabledError,
    MoltbookRateLimitError,
)
from aion.moltbook.rate_limit import SlidingWindowRateLimiter
from aion.moltbook.redact import redact_text
from aion.moltbook.settings import MoltbookSettings, load_moltbook_settings

# Paths that Phase 1 may call.
_READ_METHODS = frozenset({"GET", "HEAD"})


class MoltbookClient:
    """Minimal async client for AION's Moltbook identity (read-only Phase 1)."""

    def __init__(
        self,
        settings: MoltbookSettings,
        *,
        audit: AuditLogger | None = None,
        approval_gate: OutboundApprovalGate | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.audit = audit or AuditLogger(path=settings.audit_log_path)
        self.approval_gate = approval_gate or OutboundApprovalGate()
        self._transport = transport
        self._limiter = SlidingWindowRateLimiter(
            max_calls=settings.rate_limit_per_minute,
            window_seconds=60.0,
        )

    @classmethod
    def from_config(cls) -> "MoltbookClient":
        """Build a client from environment settings (validated)."""
        return cls(load_moltbook_settings())

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.settings.user_agent,
            "Accept": "application/json",
        }
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers

    async def _sleep_backoff(self, attempt: int, *, retry_after: float | None) -> None:
        if retry_after is not None and retry_after > 0:
            await asyncio.sleep(min(retry_after, 60.0))
            return
        # Exponential backoff with jitter bounded for interactive use.
        delay = min(2**attempt, 16) + (0.05 * attempt)
        await asyncio.sleep(delay)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        action: str,
    ) -> dict[str, Any]:
        method_upper = method.upper()
        if method_upper not in _READ_METHODS:
            raise MoltbookOutboundDisabledError(
                f"HTTP {method_upper} is disabled in Phase 1 (path={path})"
            )

        started = time.perf_counter()
        try:
            self._limiter.acquire()
        except MoltbookRateLimitError as exc:
            self.audit.record(
                AuditEvent(
                    action=action,
                    mode=self.settings.mode,
                    method=method_upper,
                    path=path,
                    success=False,
                    error=str(exc),
                    metadata={"retry_after_seconds": exc.retry_after_seconds},
                )
            )
            raise

        if self.settings.is_mock:
            raise MoltbookError(
                "Internal error: live _request invoked while mode=mock"
            )

        last_error: Exception | None = None
        attempts = self.settings.max_retries + 1
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.request(
                        method_upper,
                        f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}",
                        headers=self._headers,
                        json=json,
                        params=params,
                    )

                if response.status_code == 429:
                    retry_after_header = response.headers.get("Retry-After")
                    retry_after = (
                        float(retry_after_header)
                        if retry_after_header and retry_after_header.isdigit()
                        else None
                    )
                    if attempt + 1 < attempts:
                        await self._sleep_backoff(attempt, retry_after=retry_after)
                        continue
                    body = redact_text(response.text[:500])
                    raise MoltbookRateLimitError(
                        f"Moltbook rate limit on {method_upper} {path}: {body}",
                        retry_after_seconds=retry_after,
                    )

                if response.status_code >= 500 and attempt + 1 < attempts:
                    await self._sleep_backoff(attempt, retry_after=None)
                    continue

                if response.status_code >= 400:
                    body = redact_text(response.text[:1000])
                    raise MoltbookError(
                        f"Moltbook {method_upper} {path} failed with "
                        f"{response.status_code}: {body}"
                    )

                payload: dict[str, Any]
                if not response.content:
                    payload = {}
                else:
                    payload = response.json()
                    if not isinstance(payload, dict):
                        payload = {"data": payload}
                # Tag every live payload so callers treat it as untrusted data.
                payload.setdefault("untrusted", True)

                self.audit.record(
                    AuditEvent(
                        action=action,
                        mode=self.settings.mode,
                        method=method_upper,
                        path=path,
                        success=True,
                        status_code=response.status_code,
                        duration_ms=(time.perf_counter() - started) * 1000,
                        metadata={"attempt": attempt + 1},
                    )
                )
                return payload

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await self._sleep_backoff(attempt, retry_after=None)
                    continue
                break
            except (MoltbookError, MoltbookRateLimitError) as exc:
                self.audit.record(
                    AuditEvent(
                        action=action,
                        mode=self.settings.mode,
                        method=method_upper,
                        path=path,
                        success=False,
                        duration_ms=(time.perf_counter() - started) * 1000,
                        error=redact_text(str(exc)),
                        metadata={"attempt": attempt + 1},
                    )
                )
                raise

        message = redact_text(str(last_error) if last_error else "unknown transport error")
        self.audit.record(
            AuditEvent(
                action=action,
                mode=self.settings.mode,
                method=method_upper,
                path=path,
                success=False,
                duration_ms=(time.perf_counter() - started) * 1000,
                error=message,
            )
        )
        raise MoltbookError(f"Moltbook {method_upper} {path} failed: {message}")

    async def _mock_or_request(
        self,
        *,
        action: str,
        method: str,
        path: str,
        mock_payload: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.settings.is_mock:
            started = time.perf_counter()
            self.audit.record(
                AuditEvent(
                    action=action,
                    mode="mock",
                    method=method.upper(),
                    path=path,
                    success=True,
                    status_code=200,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    metadata={"params": params or {}},
                )
            )
            return mock_payload
        return await self._request(
            method, path, params=params, action=action
        )

    # --- Read-only operations -------------------------------------------------

    async def profile(self) -> dict[str, Any]:
        return await self._mock_or_request(
            action="profile",
            method="GET",
            path="/agents/me",
            mock_payload=mock_data.mock_profile(),
        )

    async def status(self) -> dict[str, Any]:
        return await self._mock_or_request(
            action="status",
            method="GET",
            path="/agents/status",
            mock_payload=mock_data.mock_status(),
        )

    async def feed(
        self,
        *,
        sort: str = "hot",
        limit: int = 25,
        cursor: str | None = None,
        submolt: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"sort": sort, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        if submolt:
            params["submolt"] = submolt
        return await self._mock_or_request(
            action="feed",
            method="GET",
            path="/posts",
            params=params,
            mock_payload=mock_data.mock_feed(sort=sort, limit=limit),
        )

    async def get_post(self, post_id: str) -> dict[str, Any]:
        return await self._mock_or_request(
            action="get_post",
            method="GET",
            path=f"/posts/{post_id}",
            mock_payload=mock_data.mock_post(post_id),
        )

    async def get_comments(
        self,
        post_id: str,
        *,
        sort: str = "best",
        limit: int = 35,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"sort": sort, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return await self._mock_or_request(
            action="get_comments",
            method="GET",
            path=f"/posts/{post_id}/comments",
            params=params,
            mock_payload=mock_data.mock_comments(post_id, sort=sort, limit=limit),
        )

    async def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        params: dict[str, Any] = {"q": query, "limit": limit}
        return await self._mock_or_request(
            action="search",
            method="GET",
            path="/search",
            params=params,
            mock_payload=mock_data.mock_search(query, limit=limit),
        )

    async def list_submolts(self) -> dict[str, Any]:
        return await self._mock_or_request(
            action="list_submolts",
            method="GET",
            path="/submolts",
            mock_payload=mock_data.mock_submolts(),
        )

    async def get_submolt(self, name: str) -> dict[str, Any]:
        return await self._mock_or_request(
            action="get_submolt",
            method="GET",
            path=f"/submolts/{name}",
            mock_payload=mock_data.mock_submolt(name),
        )

    # --- Disabled outbound stubs (preserved for Phase 2 approval wiring) ------

    def _deny_outbound(
        self,
        action: OutboundAction,
        *,
        summary: str,
        payload: dict[str, Any],
    ) -> None:
        request = self.approval_gate.propose(
            action, summary=summary, payload=payload
        )
        self.audit.record(
            AuditEvent(
                action=f"outbound_blocked:{action.value}",
                mode=self.settings.mode,
                method="POST",
                path="(blocked)",
                success=False,
                error="outbound disabled in Phase 1",
                metadata={"approval_request_id": request.request_id},
            )
        )
        self.approval_gate.assert_executable(request)

    async def create_post(
        self,
        *,
        submolt: str,
        title: str,
        content: str,
    ) -> dict[str, Any]:
        self._deny_outbound(
            OutboundAction.CREATE_POST,
            summary=f"Create post in {submolt}: {title[:80]}",
            payload={"submolt": submolt, "title": title, "content": content},
        )
        raise MoltbookOutboundDisabledError("unreachable")

    async def comment(
        self,
        *,
        post_id: str,
        content: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        self._deny_outbound(
            OutboundAction.COMMENT,
            summary=f"Comment on post {post_id}",
            payload={
                "post_id": post_id,
                "content": content,
                "parent_id": parent_id,
            },
        )
        raise MoltbookOutboundDisabledError("unreachable")

    async def subscribe(self, submolt: str) -> dict[str, Any]:
        self._deny_outbound(
            OutboundAction.SUBSCRIBE,
            summary=f"Subscribe to submolt {submolt}",
            payload={"submolt": submolt},
        )
        raise MoltbookOutboundDisabledError("unreachable")

    async def follow(self, agent_name: str) -> dict[str, Any]:
        self._deny_outbound(
            OutboundAction.FOLLOW,
            summary=f"Follow agent {agent_name}",
            payload={"agent_name": agent_name},
        )
        raise MoltbookOutboundDisabledError("unreachable")


def create_client(
    settings: MoltbookSettings | None = None,
    **kwargs: Any,
) -> MoltbookClient:
    """Factory used by app startup and tests."""
    resolved = settings if settings is not None else load_moltbook_settings()
    return MoltbookClient(resolved, **kwargs)


async def register_agent(
    *,
    name: str,
    description: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Registration creates credentials and is blocked in Phase 1.

    Owner-initiated registration should be performed manually outside this
    runtime until Phase 2 approval tooling is accepted. See
    ``identity/MOLTBOOK_EMISSARY.md``.
    """
    del name, description, base_url  # unused — intentionally blocked
    raise MoltbookOutboundDisabledError(
        "Agent registration is disabled in Phase 1. Register manually using "
        "the official Moltbook flow, store MOLTBOOK_API_KEY privately, then "
        "enable MOLTBOOK_MODE=live for read-only access."
    )


def validate_startup_settings() -> MoltbookSettings:
    """Validate Moltbook settings at process start without requiring live mode."""
    try:
        return load_moltbook_settings()
    except MoltbookConfigError:
        raise
