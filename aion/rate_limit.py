"""Local request rate limiting for public AION endpoints.

IMPORTANT — process-local caveat
---------------------------------
This implementation stores timestamps in an in-process dict.  On Vercel Python
functions each cold start is a fresh process, so the budget is per-isolate, not
per-client fleet.  A burst of concurrent requests can fan out across multiple
isolates and each will allow its full quota.

For a production fleet-wide limiter, replace the in-process dict with Vercel KV
(``@vercel/kv``) or Upstash Redis and use atomic increment + TTL.  The
``ClientSlidingWindowRateLimiter`` interface should remain the same so call sites
need no changes.
"""

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