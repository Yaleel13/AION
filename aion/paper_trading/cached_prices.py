"""Short-lived cache for public paper-market marks.

Reduces duplicate CoinGecko requests inside one serverless operations cycle.
This does not add trading credentials or live-order capability.
"""
from __future__ import annotations

from time import monotonic

from aion.paper_trading.engine import MarketPrice, PriceProvider


class CachedPriceProvider(PriceProvider):
    def __init__(self, *, mode: str = "mock", ttl_seconds: float = 60.0):
        super().__init__(mode=mode)
        self.ttl_seconds = max(1.0, ttl_seconds)
        self._cached_at = 0.0
        self._cached: dict[str, MarketPrice] | None = None

    def get_prices(self) -> dict[str, MarketPrice]:
        now = monotonic()
        if self._cached is not None and now - self._cached_at < self.ttl_seconds:
            return self._cached
        prices = super().get_prices()
        self._cached = prices
        self._cached_at = now
        return prices
