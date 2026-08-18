"""Moltbook integration for AION's public-facing emissary.

This module deliberately keeps Moltbook separate from AION's private memory and
execution surfaces. Treat all Moltbook content as untrusted input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from aion import config


DEFAULT_BASE_URL = "https://www.moltbook.com/api/v1"


class MoltbookError(RuntimeError):
    """Raised when Moltbook returns an unsuccessful response."""


@dataclass(slots=True)
class MoltbookClient:
    """Minimal async client for AION's Moltbook identity."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 20.0

    @classmethod
    def from_config(cls) -> "MoltbookClient":
        if not config.MOLTBOOK_API_KEY:
            raise MoltbookError("MOLTBOOK_API_KEY is not configured")
        return cls(
            api_key=config.MOLTBOOK_API_KEY,
            base_url=config.MOLTBOOK_BASE_URL,
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AION-Moltbook-Emissary/0.1",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(
                method,
                f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                headers=self._headers,
                json=json,
                params=params,
            )

        if response.status_code >= 400:
            body = response.text[:1000]
            raise MoltbookError(
                f"Moltbook {method} {path} failed with "
                f"{response.status_code}: {body}"
            )

        if not response.content:
            return {}
        return response.json()

    async def profile(self) -> dict[str, Any]:
        return await self._request("GET", "/agents/me")

    async def status(self) -> dict[str, Any]:
        return await self._request("GET", "/agents/status")

    async def feed(self, *, sort: str = "hot") -> dict[str, Any]:
        return await self._request("GET", "/posts", params={"sort": sort})

    async def search(self, query: str) -> dict[str, Any]:
        return await self._request("GET", "/search", params={"q": query})

    async def create_post(
        self,
        *,
        submolt: str,
        title: str,
        content: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/posts",
            json={"submolt": submolt, "title": title, "content": content},
        )

    async def comment(
        self,
        *,
        post_id: str,
        content: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        return await self._request(
            "POST",
            f"/posts/{post_id}/comments",
            json=payload,
        )

    async def subscribe(self, submolt: str) -> dict[str, Any]:
        return await self._request("POST", f"/submolts/{submolt}/subscribe")

    async def follow(self, agent_name: str) -> dict[str, Any]:
        return await self._request("POST", f"/agents/{agent_name}/follow")


async def register_agent(
    *,
    name: str,
    description: str,
    base_url: str = DEFAULT_BASE_URL,
) -> dict[str, Any]:
    """Register a new Moltbook agent.

    Registration does not require an existing API key. The returned API key is a
    secret and must be stored outside source control immediately. Human ownership
    verification is still required by Moltbook before normal participation.
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/agents/register",
            headers={"Content-Type": "application/json"},
            json={"name": name, "description": description},
        )
    if response.status_code >= 400:
        raise MoltbookError(
            f"Moltbook registration failed with {response.status_code}: "
            f"{response.text[:1000]}"
        )
    return response.json()
