"""Helpers for the 14-day Moltbook experiment operations cycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def customize_lead_response(lead: dict[str, Any]) -> str:
    service = str(lead.get("relevant_service") or "technical help")
    problem = str(lead.get("stated_problem") or "the issue you described")
    return (
        f"Public reply draft (owner approval still required before any off-platform move):\n\n"
        f"I noticed you described a need around “{problem[:140]}”. "
        f"One practical first step is a short, non-sensitive diagnostic: symptoms, when it started, "
        f"and what you already tried. YaliTek Online’s relevant offering here is {service} — "
        f"reviewed delivery, not unattended automation.\n\n"
        f"If a public reply is appropriate, I can share a lightweight checklist first "
        f"(useful even if you never hire anyone). I will not ask for credentials, files, "
        f"or access in public, and I will not quote pricing here."
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
