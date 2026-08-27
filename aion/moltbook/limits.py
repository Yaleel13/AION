"""Outbound quotas for Phase 2 controlled growth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from aion.moltbook.errors import MoltbookError
from aion.moltbook.security import utc_now
from aion.moltbook.store import Phase2Store


class QuotaExceededError(MoltbookError):
    """Raised when an outbound proposal would exceed owner policy caps."""


@dataclass(frozen=True, slots=True)
class OutboundQuotas:
    max_posts_per_24h: int = 1
    max_comments_per_24h: int = 3
    max_follows_per_7d: int = 5


_QUOTA_DECISIONS = ("pending", "approved", "executed")


class QuotaGuard:
    def __init__(self, store: Phase2Store, quotas: OutboundQuotas | None = None):
        self.store = store
        self.quotas = quotas or OutboundQuotas()

    def assert_can_propose(self, action: str) -> None:
        now = utc_now()
        if action == "create_post":
            since = (now - timedelta(hours=24)).isoformat()
            count = self.store.count_approvals_since(
                action=action, since_iso=since, decisions=_QUOTA_DECISIONS
            )
            if count >= self.quotas.max_posts_per_24h:
                raise QuotaExceededError(
                    f"Post quota exceeded: max {self.quotas.max_posts_per_24h} / 24h"
                )
        elif action == "comment":
            since = (now - timedelta(hours=24)).isoformat()
            count = self.store.count_approvals_since(
                action=action, since_iso=since, decisions=_QUOTA_DECISIONS
            )
            if count >= self.quotas.max_comments_per_24h:
                raise QuotaExceededError(
                    f"Comment quota exceeded: max {self.quotas.max_comments_per_24h} / 24h"
                )
        elif action == "follow":
            since = (now - timedelta(days=7)).isoformat()
            count = self.store.count_approvals_since(
                action=action, since_iso=since, decisions=_QUOTA_DECISIONS
            )
            if count >= self.quotas.max_follows_per_7d:
                raise QuotaExceededError(
                    f"Follow quota exceeded: max {self.quotas.max_follows_per_7d} / week"
                )
        elif action == "direct_message":
            raise QuotaExceededError(
                "Unsolicited direct messages are forbidden in Phase 2 policy"
            )
