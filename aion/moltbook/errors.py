"""Errors for the Moltbook integration."""

from __future__ import annotations


class MoltbookError(RuntimeError):
    """Raised when a Moltbook operation fails."""


class MoltbookConfigError(MoltbookError):
    """Raised when Moltbook configuration is invalid or incomplete."""


class MoltbookOutboundDisabledError(MoltbookError):
    """Raised when an outbound/write action is attempted during Phase 1."""


class MoltbookRateLimitError(MoltbookError):
    """Raised when local or remote rate limits block a request."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
