"""Helpers for the 14-day Moltbook experiment operations cycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aion.revenue.external_leads import is_direct_sales_source
from aion.revenue.product_catalog import match_product_for_lead

_LEAD_COLUMNS = (
    "lead_id",
    "source_url",
    "requester_identity",
    "stated_problem",
    "relevant_service",
    "fit_score",
    "confidence_score",
    "suggested_response",
    "risks",
    "approval_status",
    "conversion_outcome",
    "revenue_attributed",
    "raw_excerpt",
    "created_at",
    "content_hash",
)


def persistable_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """Drop conversion-selection extras so upsert_lead stays schema-safe."""
    return {key: lead[key] for key in _LEAD_COLUMNS if key in lead}


def _conversion_path(product: Any) -> str:
    """Return the strongest truthful conversion path currently available."""
    if getattr(product, "checkout_url", None):
        return "verified_direct_checkout"
    if getattr(product, "public_url", None) and str(getattr(product, "sale_status", "")).startswith("live"):
        return "live_site_checkout"
    if getattr(product, "public_url", None):
        return "public_offer_or_proposal"
    return "none"


def _conversion_path_rank(path: str) -> int:
    return {
        "verified_direct_checkout": 3,
        "live_site_checkout": 2,
        "public_offer_or_proposal": 1,
        "none": 0,
    }.get(path, 0)


def customize_lead_response(lead: dict[str, Any]) -> str:
    """Create a concise, human-sounding public reply that moves a buyer toward a real next step.

    Design principles:
    - First-person, direct address — reads like a human replied, not a bot.
    - Opens by acknowledging the specific problem, not a generic greeting.
    - Checkout CTA only when confidence is high AND a verified URL exists.
    - No credentials, keys, or private data ever solicited.
    - Short: three sentences max for the high-confidence case.
    """
    service = str(lead.get("relevant_service") or "technical work")
    problem = str(lead.get("stated_problem") or "the issue you described")
    confidence = float(lead.get("confidence_score") or 0.0)
    product = match_product_for_lead(lead)

    checkout_url = str(lead.get("checkout_override_url") or product.checkout_url or "").strip()
    proof = getattr(product, "social_proof", "") or ""

    # High confidence + verified checkout: direct, short, checkout CTA.
    if confidence >= 0.70 and checkout_url:
        price_note = f" ({product.price_display})" if product.price_display else ""
        proof_note = f" {proof}" if proof else ""
        return (
            f"Hey — this looks like exactly what {product.venture} helps with. "
            f"{product.name}{price_note} covers {product.fulfillment}.{proof_note} "
            f"You can book it here: {checkout_url} — please don't share credentials or access codes in the thread."
        )

    # High confidence + live site (no direct checkout): route to site with scope ask.
    if confidence >= 0.70 and product.public_url:
        price_note = f" ({product.price_display})" if product.price_display else ""
        return (
            f"This sounds like a solid fit for {product.venture}'s {product.name}{price_note}. "
            f"Details and current availability are at {product.public_url} — "
            f"if you share the non-sensitive scope and timeline I can point you to the right option directly."
        )

    # Lower confidence or no checkout: acknowledge the problem and invite scoping.
    service_short = service.lower().replace("yalitek service", "").strip() or "technical work"
    return (
        f"This looks related to {service_short} — area {product.venture} covers. "
        f"What's the current error or blocker, and is there a deadline? "
        f"Happy to figure out the right next step once I know the scope."
    )


def _source_post_id(lead: dict[str, Any]) -> str:
    """Return a Moltbook post id only. Other platforms are not comment targets."""
    url = str(lead.get("source_url") or "")
    if "moltbook.com" not in url.lower():
        return ""
    marker = "/post/"
    if marker not in url:
        return ""
    tail = url.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")
    return tail if tail and "/" not in tail else ""


def conversion_channel(lead: dict[str, Any]) -> str:
    """Return how a qualified lead may be converted.

    moltbook_comment — public Moltbook reply via controlled autonomy.
    owner_direct_alert — owner sales alert + checkout; no auto-comment.
    """
    if _source_post_id(lead):
        return "moltbook_comment"
    url = str(lead.get("source_url") or "").strip()
    if url.startswith("https://") and is_direct_sales_source(url):
        return "owner_direct_alert"
    return ""


def select_conversion_candidate(leads: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick one explicit, high-confidence buyer with a real conversion path.

    Moltbook leads with a `/post/` id can be converted by a policy-gated public
    comment. Reddit, GitHub, and HN leads convert as owner sales alerts with a
    checkout link — AION never auto-comments on those platforms.

    When multiple leads qualify, AION prioritizes stronger conversion paths first
    (verified checkout > live site checkout > proposal), then confidence and fit.
    """
    eligible: list[dict[str, Any]] = []
    for lead in leads:
        confidence = float(lead.get("confidence_score") or 0.0)
        risks = str(lead.get("risks") or "")
        content = str(lead.get("suggested_response") or "")
        outcome = str(lead.get("conversion_outcome") or "uncontacted")
        post_id = _source_post_id(lead)
        channel = conversion_channel(lead)
        if confidence < 0.70 or not content or not channel:
            continue
        if outcome not in {"uncontacted", "", "none"}:
            continue
        if "intent_signal=explicit" not in risks:
            continue
        if "prompt-injection heuristics matched" in risks:
            continue
        if channel == "moltbook_comment" and not post_id:
            continue

        product = match_product_for_lead(lead)
        path = _conversion_path(product)
        if path == "none":
            continue

        item = dict(lead)
        item["source_post_id"] = post_id
        item["conversion_channel"] = channel
        item["matched_product_key"] = product.product_key
        item["matched_venture"] = product.venture
        item["conversion_path"] = path
        item["conversion_path_rank"] = _conversion_path_rank(path)
        eligible.append(item)

    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda item: (
            int(item.get("conversion_path_rank") or 0),
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
