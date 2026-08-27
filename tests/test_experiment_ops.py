"""Unit tests for experiment ops cycle helpers (no live network)."""

from __future__ import annotations

from datetime import datetime, timezone

from aion.moltbook.experiment_ops import (
    customize_lead_response,
    refresh_queue_timing,
    select_next_campaign_draft,
)


def test_customize_lead_response_includes_yalitek_and_no_pricing() -> None:
    text = customize_lead_response(
        {
            "relevant_service": "systems debugging",
            "stated_problem": "agent queue keeps double-posting",
        }
    )
    assert "systems debugging" in text
    assert "YaliTek" in text
    assert "will not quote pricing" in text
    assert "credentials" in text


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
