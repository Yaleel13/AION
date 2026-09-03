from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aion.buyer_inventory import (
    DAILY_TARGET_MAX,
    DAILY_TARGET_MIN,
    QUALIFIED_BUYER_SCORE,
    InventoryCandidate,
    extract_candidates,
    inventory_sources,
    score_candidate,
)
from aion.external_scouts import PublicSource


def _epoch(hours_ago: int) -> float:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).timestamp()


def test_fresh_explicit_paid_buyer_meets_quality_threshold() -> None:
    source = PublicSource("test", "https://hn.algolia.com/api/v1/search", "commercial")
    candidate = InventoryCandidate(
        source=source,
        title="Hiring Next.js contractor",
        text=(
            "Looking to hire a freelancer for a paid Next.js and Stripe integration project. "
            "Budget $1200. Email jobs@example.com. Need to start this week."
        ),
        url="https://news.ycombinator.com/item?id=1",
        published_at="",
        published_epoch=_epoch(24),
    )
    result = score_candidate(candidate)
    assert result.qualified is True
    assert result.total >= QUALIFIED_BUYER_SCORE
    assert result.recency == 20
    assert result.contactability == 10


def test_stale_buyer_is_rejected_even_with_budget_and_fit() -> None:
    source = PublicSource("test", "https://hn.algolia.com/api/v1/search", "commercial")
    candidate = InventoryCandidate(
        source=source,
        title="Hiring React developer",
        text="Looking to hire a developer for a paid React website. Budget $2000. Email jobs@example.com.",
        url="https://news.ycombinator.com/item?id=2",
        published_at="",
        published_epoch=_epoch(8 * 24),
    )
    result = score_candidate(candidate)
    assert result.qualified is False
    assert result.recency == 0


def test_unknown_age_requires_explicit_still_open_language() -> None:
    source = PublicSource("test", "https://hn.algolia.com/api/v1/search", "commercial")
    candidate = InventoryCandidate(
        source=source,
        title="Hiring automation contractor",
        text=(
            "Currently hiring a contractor for a paid n8n automation project. "
            "Budget $900. Apply by email jobs@example.com."
        ),
        url="https://news.ycombinator.com/item?id=3",
        published_at="",
        published_epoch=None,
    )
    result = score_candidate(candidate)
    assert result.qualified is True
    assert result.recency == 12


def test_extract_candidates_reads_github_timestamp_and_open_state() -> None:
    source = PublicSource(
        "github_hiring_nextjs",
        "https://api.github.com/search/issues?q=hiring+next.js+is%3Aissue+is%3Aopen",
        "github",
    )
    payload = {
        "items": [
            {
                "state": "open",
                "title": "Hiring Next.js contractor",
                "body": "Looking to hire a freelancer for a paid Next.js website. Budget $1000.",
                "html_url": "https://github.com/acme/app/issues/1",
                "created_at": "2026-09-03T12:00:00Z",
            }
        ]
    }
    candidates = extract_candidates(payload, source)
    assert len(candidates) == 1
    assert candidates[0].published_epoch is not None
    assert candidates[0].published_at.startswith("2026-09-03T12:00:00")


def test_closed_github_issue_never_enters_inventory() -> None:
    source = PublicSource(
        "github_hiring_nextjs",
        "https://api.github.com/search/issues?q=hiring+next.js+is%3Aissue+is%3Aopen",
        "github",
    )
    payload = {
        "items": [
            {
                "state": "closed",
                "title": "Hiring Next.js contractor",
                "body": "Looking to hire a freelancer for a paid Next.js website. Budget $1000.",
                "html_url": "https://github.com/acme/app/issues/2",
                "created_at": "2026-09-03T12:00:00Z",
            }
        ]
    }
    assert extract_candidates(payload, source) == []


def test_source_mix_is_broad_enough_for_inventory_discovery() -> None:
    sources = inventory_sources()
    commercial_sources = [source for source in sources if source.scout in {"commercial", "reddit", "github"}]
    assert DAILY_TARGET_MIN == 10
    assert DAILY_TARGET_MAX == 20
    assert len(commercial_sources) >= DAILY_TARGET_MIN
    assert len({source.url for source in sources}) == len(sources)
