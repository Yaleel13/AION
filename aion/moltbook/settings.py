"""Typed Moltbook configuration validated at load time."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from aion.moltbook.errors import MoltbookConfigError

MoltbookMode = Literal["mock", "live"]

DEFAULT_BASE_URL = "https://www.moltbook.com/api/v1"
ALLOWED_LIVE_HOSTS = frozenset({"www.moltbook.com"})


@dataclass(frozen=True, slots=True)
class MoltbookSettings:
    """Validated settings for AION's Moltbook access.

    Read-only access remains the default. Controlled outbound is available only
    when both explicit owner gates are enabled; the normal read client still
    refuses non-GET methods even when these flags are true.
    """

    mode: MoltbookMode = "mock"
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 20.0
    max_retries: int = 3
    rate_limit_per_minute: int = 30
    outbound_enabled: bool = False
    execute_enabled: bool = False
    audit_log_path: str | None = None
    user_agent: str = "AION-Moltbook-Emissary/0.3-controlled"

    def __repr__(self) -> str:
        key_state = "set" if self.api_key else "unset"
        return (
            "MoltbookSettings("
            f"mode={self.mode!r}, "
            f"api_key=<{key_state}>, "
            f"base_url={self.base_url!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"max_retries={self.max_retries!r}, "
            f"rate_limit_per_minute={self.rate_limit_per_minute!r}, "
            f"outbound_enabled={self.outbound_enabled!r}, "
            f"execute_enabled={self.execute_enabled!r}, "
            f"audit_log_path={self.audit_log_path!r}, "
            f"user_agent={self.user_agent!r})"
        )

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @property
    def configured_for_live(self) -> bool:
        return bool(self.api_key) and self.is_live

    @property
    def controlled_outbound_ready(self) -> bool:
        return self.configured_for_live and self.outbound_enabled and self.execute_enabled


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_mode(value: str | None) -> MoltbookMode:
    raw = (value or "mock").strip().lower()
    if raw not in {"mock", "live"}:
        raise MoltbookConfigError(
            f"MOLTBOOK_MODE must be 'mock' or 'live', got {raw!r}"
        )
    return raw  # type: ignore[return-value]


def _validate_base_url(base_url: str, *, mode: MoltbookMode) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme != "https":
        raise MoltbookConfigError("MOLTBOOK_BASE_URL must use https")
    if not parsed.netloc:
        raise MoltbookConfigError("MOLTBOOK_BASE_URL is missing a host")
    if mode == "live" and parsed.hostname not in ALLOWED_LIVE_HOSTS:
        raise MoltbookConfigError(
            "Live MOLTBOOK_BASE_URL host must be www.moltbook.com "
            "(non-www redirects strip Authorization headers)"
        )
    return base_url.rstrip("/")


def load_moltbook_settings(
    *,
    environ: dict[str, str] | None = None,
) -> MoltbookSettings:
    """Load and validate Moltbook settings from environment variables."""
    env = environ if environ is not None else dict(os.environ)

    mode = _parse_mode(env.get("MOLTBOOK_MODE"))
    api_key = (env.get("MOLTBOOK_API_KEY") or "").strip()
    base_url = _validate_base_url(
        (env.get("MOLTBOOK_BASE_URL") or DEFAULT_BASE_URL).strip(),
        mode=mode,
    )

    try:
        timeout_seconds = float(env.get("MOLTBOOK_TIMEOUT_SECONDS") or "20")
        max_retries = int(env.get("MOLTBOOK_MAX_RETRIES") or "3")
        rate_limit_per_minute = int(env.get("MOLTBOOK_RATE_LIMIT_PER_MINUTE") or "30")
    except ValueError as exc:
        raise MoltbookConfigError(
            "Invalid numeric Moltbook setting "
            "(timeout, retries, or rate limit)"
        ) from exc

    if timeout_seconds <= 0:
        raise MoltbookConfigError("MOLTBOOK_TIMEOUT_SECONDS must be > 0")
    if max_retries < 0 or max_retries > 10:
        raise MoltbookConfigError("MOLTBOOK_MAX_RETRIES must be between 0 and 10")
    if rate_limit_per_minute < 1 or rate_limit_per_minute > 60:
        raise MoltbookConfigError("MOLTBOOK_RATE_LIMIT_PER_MINUTE must be between 1 and 60")

    outbound_enabled = _parse_bool(env.get("MOLTBOOK_OUTBOUND_ENABLED"), False)
    execute_enabled = _parse_bool(env.get("MOLTBOOK_EXECUTE_ENABLED"), False)
    if execute_enabled and not outbound_enabled:
        raise MoltbookConfigError(
            "MOLTBOOK_EXECUTE_ENABLED requires MOLTBOOK_OUTBOUND_ENABLED=true"
        )
    if (outbound_enabled or execute_enabled) and mode != "live":
        raise MoltbookConfigError(
            "MOLTBOOK_OUTBOUND_ENABLED requires MOLTBOOK_MODE=live; controlled execution also requires the separate MOLTBOOK_EXECUTE_ENABLED gate"
        )

    audit_log_path = (env.get("MOLTBOOK_AUDIT_LOG_PATH") or "").strip() or None

    if mode == "live" and not api_key:
        raise MoltbookConfigError("MOLTBOOK_API_KEY is required when MOLTBOOK_MODE=live")

    return MoltbookSettings(
        mode=mode,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        rate_limit_per_minute=rate_limit_per_minute,
        outbound_enabled=outbound_enabled,
        execute_enabled=execute_enabled,
        audit_log_path=audit_log_path,
    )
