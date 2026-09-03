"""Unit tests for experiment ops cycle helpers (no live network)."""

from __future__ import annotations

from datetime import datetime, timezone

from aion.moltbook.experiment_ops import (
    customize_lead_response,
    mark_backlog_status,
    refresh_queue_timing,
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
