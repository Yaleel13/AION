"""Unit tests for experiment ops cycle helpers (no live network)."""

from __future__ import annotations

from datetime import datetime, timezone

from aion.moltbook.experiment_ops import (
    conversion_channel,
    customize_lead_response,
    mark_backlog_status,
    persistable_lead,
    refresh_queue_timing,
    select_conversion_candidate,
    select_next_backlog_comment,
    select_next_campaign_draft,
)
from aion.revenue.product_catalog import PRODUCTS

_QUICK_DIAG = next(p for p in PRODUCTS if p.product_key == "quick-tech-diagnostic")
YALITEK_QUICK_DIAGNOSTIC_URL: str = _QUICK_DIAG.checkout_url or _QUICK_DIAG.public_url


def test_customize_lead_response_high_confidence_adds_checkout() -> None:
    text = customize_lead_response(
        {
            "relevant_service": "systems debugging",
            "stated_problem": "agent queue keeps double-posting",
            "confidence_score": 0.85,
        }
    )
    # New human-sounding reply: opens with "Hey", names the venture, includes checkout.
    assert "YaliTek" in text
    assert _QUICK_DIAG.name in text
    assert (_QUICK_DIAG.price_display or "") in text
    assert YALITEK_QUICK_DIAGNOSTIC_URL in text
    # Must remind buyer not to share credentials.
    assert "credential" in text.lower() or "access code" in text.lower()


def test_customize_lead_response_lower_confidence_stays_scope_first() -> None:
    text = customize_lead_response(
        {
            "relevant_service": "website repair",
            "stated_problem": "site seems flaky",
            "confidence_score": 0.55,
        }
    )
    # Lower confidence: no checkout URL, asks for scope/deadline.
    assert YALITEK_QUICK_DIAGNOSTIC_URL not in text
    assert "scope" in text.lower() or "deadline" in text.lower() or "blocker" in text.lower()


def test_select_next_campaign_draft_skips_linked() -> None:
    drafts = [
        {"draft_id": "b", "day_index": 2, "approval_request_id": None, "title": "two"},
        {
            "draft_id": "a",
            "day_index": 1,
            "approval_request_id": "autonomy:post-1",
            "title": "one",
        },
        {"draft_id": "c", "day_index": 3, "approval_request_id": None, "title": "three"},
    ]
    nxt = select_next_campaign_draft(drafts)
    assert nxt is not None
    assert nxt["draft_id"] == "b"
    assert nxt["day_index"] == 2


def test_refresh_queue_timing_updates_seconds() -> None:
    queued = {
        "type": "queued_comment",
        "post_id": "abc",
        "publish_when": {
            "first_slot_frees_at": "2026-08-28T10:12:15+00:00",
            "seconds_remaining": 999999,
        },
    }
    now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    refreshed = refresh_queue_timing(queued, now=now)
    assert refreshed["publish_when"]["seconds_remaining"] == 79935
    assert refreshed["publish_when"]["first_slot_frees_at"] == "2026-08-28T10:12:15+00:00"


def test_select_next_backlog_comment_by_priority() -> None:
    backlog = [
        {
            "priority": 5,
            "status": "ready",
            "policy_allowed": True,
            "post_id": "p5",
            "content": "later",
        },
        {
            "priority": 2,
            "status": "ready",
            "policy_allowed": True,
            "post_id": "p2",
            "content": "sooner",
        },
        {
            "priority": 1,
            "status": "primary_queue",
            "policy_allowed": True,
            "post_id": "p1",
            "content": None,
        },
    ]
    nxt = select_next_backlog_comment(backlog)
    assert nxt is not None
    assert nxt["post_id"] == "p2"


def test_mark_backlog_status() -> None:
    backlog = [
        {"priority": 2, "post_id": "p2", "content": "x", "status": "ready"},
        {"priority": 3, "post_id": "p3", "content": "y", "status": "ready"},
    ]
    updated = mark_backlog_status(backlog, post_id="p2", priority=2, status="published")
    assert updated[0]["status"] == "published"
    assert updated[1]["status"] == "ready"


def _explicit_lead(**overrides: object) -> dict:
    row = {
        "lead_id": "lead-1",
        "source_url": "https://www.moltbook.com/post/abc123",
        "stated_problem": "Need help debugging a production Next.js outage",
        "relevant_service": "Technical diagnostics",
        "confidence_score": 0.85,
        "fit_score": 0.8,
        "suggested_response": "Hey — I can help with a diagnostic.",
        "risks": "intent_signal=explicit; monetization_track=yalitek_service",
        "approval_status": "pending_owner_review",
        "conversion_outcome": "uncontacted",
        "revenue_attributed": 0.0,
        "raw_excerpt": "Need help debugging a production Next.js outage",
        "created_at": "2026-09-03T00:00:00+00:00",
        "content_hash": "hash-1",
        "requester_identity": "buyer",
    }
    row.update(overrides)
    return row


def test_select_conversion_candidate_accepts_moltbook_post() -> None:
    chosen = select_conversion_candidate([_explicit_lead()])
    assert chosen is not None
    assert chosen["conversion_channel"] == "moltbook_comment"
    assert chosen["source_post_id"] == "abc123"


def test_select_conversion_candidate_accepts_reddit_as_owner_alert() -> None:
    chosen = select_conversion_candidate(
        [
            _explicit_lead(
                lead_id="lead-reddit",
                source_url="https://www.reddit.com/r/forhire/comments/xyz/hiring/",
            )
        ]
    )
    assert chosen is not None
    assert chosen["conversion_channel"] == "owner_direct_alert"
    assert chosen["source_post_id"] == ""


def test_select_conversion_candidate_skips_already_converted() -> None:
    chosen = select_conversion_candidate(
        [_explicit_lead(conversion_outcome="owner_sales_alert")]
    )
    assert chosen is None


def test_conversion_channel_ignores_non_moltbook_post_paths() -> None:
    assert conversion_channel({"source_url": "https://example.com/post/nope"}) == ""
    assert conversion_channel({"source_url": "https://news.ycombinator.com/item?id=1"}) == "owner_direct_alert"


def test_persistable_lead_drops_selection_extras() -> None:
    row = persistable_lead(
        _explicit_lead(conversion_channel="moltbook_comment", matched_product_key="quick-tech-diagnostic")
    )
    assert "conversion_channel" not in row
    assert "matched_product_key" not in row
    assert row["lead_id"] == "lead-1"
