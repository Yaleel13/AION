"""Helpers for the 14-day Moltbook experiment operations cycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aion.revenue.product_catalog import match_product_for_lead


def customize_lead_response(lead: dict[str, Any]) -> str:
    """Create a concise, buyer-oriented public reply without overclaiming.

    The reply is designed to move a legitimate public request toward the most
    relevant creator-authorized product while keeping credentials, private files,
    custom pricing negotiation, and sensitive payment details out of the public
    thread.

    A direct checkout CTA is only added when both buyer confidence is high and the
    matched product has a verified checkout URL. Otherwise AION uses a truthful
    product/site/proposal route instead of inventing a payment path.
    """
    service = str(lead.get("relevant_service") or "technical help")
    problem = str(lead.get("stated_problem") or "the issue you described")
    confidence = float(lead.get("confidence_score") or 0.0)
    product = match_product_for_lead(lead)

    base = (
        f"I saw your request around \"{problem[:120]}\". "
        f"AION matched this to {product.venture}'s {product.name}, which fits {service.lower()}. "
    )

    if confidence >= 0.70 and product.checkout_url:
        price = f" ({product.price_display})" if product.price_display else ""
        return (
            base
            + f"If you want to move forward, the verified checkout is here{price}: "
            + product.checkout_url
            + f". The current fulfillment is {product.fulfillment}. "
            "Please do not post credentials, private keys, access codes, or customer data here."
        )

    if confidence >= 0.70 and product.public_url:
        price = f" Current listed plan: {product.price_display}." if product.price_display else ""
        return (
            base
            + f"You can review the current offer here: {product.public_url}."
            + price
            + " If you share the non-sensitive scope, desired outcome, and deadline, I can route you to the correct existing offer or proposal path. "
            "Please do not post credentials, private keys, access codes, or customer data here."
        )

    return (
        base
        + "If this is still open, reply with the non-sensitive scope, desired outcome, "
        "and deadline. I can match that to the correct existing product and next step. "
        "Please do not post credentials, private keys, access codes, or customer data here."
    )


def _source_post_id(lead: dict[str, Any]) -> str:
    url = str(lead.get("source_url") or "")
    marker = "/post/"
    if marker not in url:
        return ""
    tail = url.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")
    return tail if tail and "/" not in tail else ""


def select_conversion_candidate(leads: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick one explicit, high-confidence public buyer-intent lead for controlled reply.

    Selection is intentionally strict: public Moltbook post, explicit buyer signal,
    confidence >= 0.70, non-hostile content, and a prepared response. The execution
    engine still applies all policy, pacing, quota, secret/PII, and idempotency gates.
    """
    eligible: list[dict[str, Any]] = []
    for lead in leads:
        confidence = float(lead.get("confidence_score") or 0.0)
        risks = str(lead.get("risks") or "")
        content = str(lead.get("suggested_response") or "")
        post_id = _source_post_id(lead)
        if confidence < 0.70 or not post_id or not content:
            continue
        if "intent_signal=explicit" not in risks:
            continue
        if "prompt-injection heuristics matched" in risks:
            continue
        item = dict(lead)
        item["source_post_id"] = post_id
        eligible.append(item)

    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda item: (
            float(item.get("confidence_score") or 0.0),
            float(item.get("fit_score") or 0.0),
        ),
        reverse=True,
    )[0]


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
