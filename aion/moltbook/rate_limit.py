"""Simple client-side rate limiter for Moltbook requests."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from aion.moltbook.errors import MoltbookRateLimitError


@dataclass(slots=True)
class SlidingWindowRateLimiter:
    """Allow at most ``max_calls`` within a rolling ``window_seconds``."""

    max_calls: int
    window_seconds: float = 60.0
    _timestamps: deque[float] = field(default_factory=deque)

    def acquire(self) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_calls:
            oldest = self._timestamps[0]
            retry_after = max(0.0, self.window_seconds - (now - oldest))
            raise MoltbookRateLimitError(
                "Local Moltbook rate limit exceeded; slow down before retrying",
                retry_after_seconds=retry_after,
            )
        self._timestamps.append(now)
