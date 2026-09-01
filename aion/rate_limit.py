"""Local request rate limiting for public AION endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


class RateLimitExceeded(Exception):
    """Raised when a request exceeds its client-specific request budget."""

    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Rate limit exceeded; retry later.")


@dataclass(slots=True)
class ClientSlidingWindowRateLimiter:
    """Allow a bounded number of requests per client within a rolling window."""

    max_requests: int
    window_seconds: float = 60.0
    _timestamps_by_client: dict[str, deque[float]] = field(
        default_factory=lambda: defaultdict(deque)
    )

    def acquire(self, client_id: str) -> None:
        now = time.monotonic()
        timestamps = self._timestamps_by_client[client_id]
        cutoff = now - self.window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= self.max_requests:
            retry_after = max(0.0, self.window_seconds - (now - timestamps[0]))
            raise RateLimitExceeded(retry_after)
        timestamps.append(now)