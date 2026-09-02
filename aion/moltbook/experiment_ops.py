"""Helpers for the 14-day Moltbook experiment operations cycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


YALITEK_QUICK_DIAGNOSTIC_URL = "https://buy.stripe.com/bJe00i66d4a17BTbFa1sQ00"


def customize_lead_response(lead: dict[str, Any]) -> str:
    """Create a concise, buyer-oriented public reply without overclaiming.

    The reply is designed to move a legitimate public request toward a scoped
    YaliTek offer while keeping credentials, private files, custom pricing
    negotiation, and sensitive payment details out of the public thread.

    A direct checkout CTA is only added for high-confidence leads. Lower-confidence
    candidates remain a scope-first conversation so AION does not spray payment
    links into ambiguous discussions.
    """
    service = str(lead.get("relevant_service") or "technical help")
    problem = str(lead.get("stated_problem") or "the issue you described")
    confidence = float(lead.get("confidence_score") or 0.0)

    base = (
        f"I saw your request around \"{problem[:120]}\". "
        f"YaliTek Online can help with {service.lower()}. "
    )
    if confidence >= 0.70:
        return (
            base
            + "If you want a fixed-scope first step, the $49 Quick Tech Diagnostic is live here: "
            + YALITEK_QUICK_DIAGNOSTIC_URL
            + ". It covers a technical diagnostic and prioritized next-step plan. "
            "Please do not post credentials, private keys, access codes, or customer data here."
        )
    return (
        base
        + "If this is still open, reply with the non-sensitive scope, desired outcome, "
        "and deadline. I can turn that into a fixed-scope next step and turnaround. "
        "Please do not post credentials, private keys, access codes, or customer data here."
    )


def refresh_queue_timing(
    queued: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Refresh seconds_remaining on a queued outbound hold without republishing."""
    if not isinstance(queued, dict) or queued.get("type") != "queued_comment":
        return queued
    publish_when = dict(queued.get("publish_when") or {})
    frees_raw = publish_when.get("first_slot_frees_at")
    if not frees_raw:
        return queued
    try:
        frees = datetime.fromisoformat(str(frees_raw))
    except ValueError:
        return queued
    if frees.tzinfo is None:
        frees = frees.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    publish_when["seconds_remaining"] = max(0, int((frees - current).total_seconds()))
    out = dict(queued)
    out["publish_when"] = publish_when
    return out


def select_next_campaign_draft(
    drafts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Pick the lowest day_index draft that has not been linked to an approval/publish."""
    awaiting = [d for d in drafts if not d.get("approval_request_id")]
    if not awaiting:
        return None
    return sorted(awaiting, key=lambda d: int(d.get("day_index") or 0))[0]


def select_next_backlog_comment(
    backlog: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Pick the highest-priority ready, policy-allowed backlog comment with content."""
    ready = [
        item
        for item in backlog
        if item.get("status") == "ready"
        and item.get("policy_allowed")
        and item.get("content")
        and item.get("post_id")
        and item.get("priority") is not None
    ]
    if not ready:
        return None
    return sorted(ready, key=lambda item: int(item.get("priority") or 10_000))[0]


def mark_backlog_status(
    backlog: list[dict[str, Any]],
    *,
    post_id: str,
    priority: int | None,
    status: str,
) -> list[dict[str, Any]]:
    """Return a copy of backlog with matching item status updated."""
    out: list[dict[str, Any]] = []
    for item in backlog:
        copy = dict(item)
        same_post = str(copy.get("post_id") or "") == str(post_id)
        same_priority = priority is None or int(copy.get("priority") or -1) == int(priority)
        if same_post and same_priority and copy.get("content"):
            copy["status"] = status
        out.append(copy)
    return out
