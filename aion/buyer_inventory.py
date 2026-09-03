"""High-intent buyer inventory for AION's scheduled revenue loop.

Discovery is deliberately broader than outbound. The engine may inspect hundreds
of public records, but it only promotes fresh, explicit, commercially relevant,
deduplicated buyers that clear a transparent quality threshold.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from aion.external_scouts import (
    PublicSource,
    ScoutCandidate,
    _allowed_hosts,
    _scout_headers,
    _validate_source,
    candidate_to_opportunity,
    default_sources,
)
from aion.opportunity_store import OpportunityStore
from aion.revenue_pipeline import _explicit_amount

QUALIFIED_BUYER_SCORE = 75
PREFERRED_FRESHNESS_HOURS = 72
MAX_FRESHNESS_HOURS = 7 * 24
DAILY_TARGET_MIN = 10
DAILY_TARGET_MAX = 20

STRONG_INTENT = re.compile(
    r"(?i)\b(looking to hire|hiring|seeking (?:a |an )?(?:developer|consultant|contractor|freelancer)|"
    r"paid (?:gig|project|contract)|request for proposals?|\brfp\b|bounty|contract opportunity|"
    r"looking for (?:a |an )?(?:developer|consultant|contractor|freelancer)|"
    r"need (?:a |an )?(?:developer|consultant|contractor|freelancer))\b"
)
SERVICE_FIT = re.compile(
    r"(?i)\b(website|wordpress|shopify|hosting|deploy|deployment|vercel|automation|workflow|n8n|zapier|"
    r"ai agent|ai integration|technical support|diagnostic|debug|landing page|startup site|next\.js|react|"
    r"typescript|tailwind|shadcn|api integration|stripe|supabase|fastapi)\b"
)
PAID_SIGNAL = re.compile(r"(?i)\b(paid|budget|rate|compensation|fixed[- ]price|hourly|usd|\$\d+)\b")
CONTACT_SIGNAL = re.compile(
    r"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\bapply\b|\bapplication\b|\bcontact\b|"
    r"\bemail\b|\breply\b|\bmessage me\b|\bdm me\b)"
)
URGENCY_SIGNAL = re.compile(
    r"(?i)\b(asap|urgent|immediately|start (?:now|today|immediately)|this week|within \d+ days?|"
    r"ready to hire|ready to start)\b"
)
STILL_OPEN_SIGNAL = re.compile(
    r"(?i)\b(still open|currently hiring|accepting applications|open role|open project|still hiring)\b"
)


@dataclass(frozen=True, slots=True)
class InventoryCandidate:
    source: PublicSource
    title: str
    text: str
    url: str
    published_at: str
    published_epoch: float | None


@dataclass(frozen=True, slots=True)
class BuyerScore:
    total: int
    qualified: bool
    age_hours: float | None
    intent: int
    recency: int
    service_fit: int
    budget: int
    contactability: int
    urgency: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.total,
            "qualified": self.qualified,
            "age_hours": round(self.age_hours, 1) if self.age_hours is not None else None,
            "dimensions": {
                "intent": self.intent,
                "recency": self.recency,
                "service_fit": self.service_fit,
                "budget": self.budget,
                "contactability": self.contactability,
                "urgency": self.urgency,
            },
        }


def _plain(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _url(value: dict[str, Any], source: PublicSource) -> str:
    permalink = str(value.get("permalink") or "").strip()
    html_url = str(value.get("html_url") or "").strip()
    url = str(value.get("url") or value.get("story_url") or "").strip()
    object_id = str(value.get("objectID") or value.get("id") or "").strip()
    if permalink.startswith("/"):
        return f"https://www.reddit.com{permalink.split('?', 1)[0]}"
    if html_url.startswith("https://"):
        return html_url
    if url.startswith("https://"):
        return url
    if object_id and "hn.algolia.com" in source.url:
        return f"https://news.ycombinator.com/item?id={object_id}"
    return ""


def _timestamp(value: dict[str, Any]) -> tuple[str, float | None]:
    for key in ("created_at_i", "created_utc"):
        raw = value.get(key)
        if isinstance(raw, (int, float)) and raw > 0:
            dt = datetime.fromtimestamp(float(raw), tz=timezone.utc)
            return dt.isoformat(), float(raw)
    for key in ("created_at", "created", "updated_at"):
        raw = str(value.get(key) or "").strip()
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat(), dt.timestamp()
        except ValueError:
            continue
    return "", None


def extract_candidates(payload: Any, source: PublicSource) -> list[InventoryCandidate]:
    candidates: list[InventoryCandidate] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if source.scout == "github" and str(value.get("state") or "").lower() == "closed":
                return
            inner = value.get("data")
            if isinstance(inner, dict) and value.get("kind"):
                visit(inner)
                return
            title = _plain(
                value.get("title")
                or value.get("story_title")
                or value.get("name")
                or value.get("subject")
                or ""
            )
            body = _plain(
                value.get("selftext")
                or value.get("description")
                or value.get("comment_text")
                or value.get("text")
                or value.get("story_text")
                or value.get("body")
                or value.get("summary")
                or ""
            )
            candidate_url = _url(value, source)
            combined = f"{title}\n{body}".strip()
            if combined and len(combined) >= 30 and candidate_url:
                if source.scout != "github" or "/issues/" in candidate_url:
                    published_at, published_epoch = _timestamp(value)
                    candidates.append(
                        InventoryCandidate(
                            source=source,
                            title=title,
                            text=combined[:6000],
                            url=candidate_url,
                            published_at=published_at,
                            published_epoch=published_epoch,
                        )
                    )
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value[:100]:
                visit(child)

    visit(payload)
    unique: dict[str, InventoryCandidate] = {}
    for candidate in candidates:
        unique.setdefault(candidate.url, candidate)
    return list(unique.values())[:100]


def score_candidate(candidate: InventoryCandidate, *, now_epoch: float | None = None) -> BuyerScore:
    text = candidate.text
    now = now_epoch if now_epoch is not None else datetime.now(timezone.utc).timestamp()
    age_hours = None
    if candidate.published_epoch is not None:
        age_hours = max(0.0, (now - candidate.published_epoch) / 3600.0)

    intent = 30 if STRONG_INTENT.search(text) else 0
    if age_hours is None:
        recency = 12 if STILL_OPEN_SIGNAL.search(text) else 0
    elif age_hours <= PREFERRED_FRESHNESS_HOURS:
        recency = 20
    elif age_hours <= MAX_FRESHNESS_HOURS:
        recency = 12
    else:
        recency = 0
    service_fit = 20 if SERVICE_FIT.search(text) else 0
    amount = _explicit_amount(text)
    budget = 15 if amount > 0 else 8 if PAID_SIGNAL.search(text) else 0
    contactability = 10 if CONTACT_SIGNAL.search(text) else 7 if candidate.url.startswith("https://") else 0
    urgency = 5 if URGENCY_SIGNAL.search(text) else 0
    total = intent + recency + service_fit + budget + contactability + urgency
    freshness_ok = (
        age_hours is not None and age_hours <= MAX_FRESHNESS_HOURS
    ) or (age_hours is None and bool(STILL_OPEN_SIGNAL.search(text)))
    qualified = bool(
        total >= QUALIFIED_BUYER_SCORE
        and intent == 30
        and service_fit == 20
        and contactability > 0
        and freshness_ok
    )
    return BuyerScore(total, qualified, age_hours, intent, recency, service_fit, budget, contactability, urgency)


def inventory_sources() -> list[PublicSource]:
    """Return a diverse public source pool sized for broad discovery, not broad outreach."""
    sources = list(default_sources())
    extras = [
        PublicSource("hn_paid_nextjs", "https://hn.algolia.com/api/v1/search_by_date?query=paid%20project%20next.js&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("hn_react_contractor", "https://hn.algolia.com/api/v1/search_by_date?query=seeking%20contractor%20react&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("hn_stripe_help", "https://hn.algolia.com/api/v1/search_by_date?query=stripe%20integration%20help&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("hn_supabase_help", "https://hn.algolia.com/api/v1/search_by_date?query=supabase%20help&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("hn_wordpress_help", "https://hn.algolia.com/api/v1/search_by_date?query=wordpress%20help&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("hn_shopify_help", "https://hn.algolia.com/api/v1/search_by_date?query=shopify%20help&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("hn_vercel_help", "https://hn.algolia.com/api/v1/search_by_date?query=vercel%20help&tags=comment&hitsPerPage=50", "commercial"),
        PublicSource("github_hiring_nextjs", "https://api.github.com/search/issues?q=hiring+next.js+is%3Aissue+is%3Aopen&sort=created&order=desc&per_page=30", "github"),
        PublicSource("github_paid_stripe", "https://api.github.com/search/issues?q=%22paid+project%22+stripe+is%3Aissue+is%3Aopen&sort=created&order=desc&per_page=30", "github"),
        PublicSource("github_hiring_react", "https://api.github.com/search/issues?q=%22looking+to+hire%22+react+is%3Aissue+is%3Aopen&sort=created&order=desc&per_page=30", "github"),
    ]
    seen = {source.url for source in sources}
    for source in extras:
        if source.url not in seen:
            sources.append(source)
            seen.add(source.url)
    return sources


class BuyerInventoryEngine:
    def __init__(self, opportunity_store: OpportunityStore, *, timeout_seconds: float = 12.0):
        self.store = opportunity_store
        self.timeout_seconds = timeout_seconds

    async def scan(self, sources: list[PublicSource] | None = None) -> dict[str, Any]:
        selected_sources = sources or inventory_sources()
        allowed = _allowed_hosts()
        errors: list[dict[str, str]] = []
        raw_count = 0
        plausible_count = 0
        seen_urls: set[str] = set()
        qualified: list[dict[str, Any]] = []
        qualified_channels: set[str] = set()

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
            for source in selected_sources:
                try:
                    _validate_source(source, allowed_hosts=allowed)
                    response = await client.get(source.url, headers=_scout_headers(source))
                    response.raise_for_status()
                    if "json" not in response.headers.get("content-type", "").lower():
                        raise ValueError("Buyer inventory source must return JSON")
                    for candidate in extract_candidates(response.json(), source):
                        raw_count += 1
                        if candidate.url in seen_urls:
                            continue
                        seen_urls.add(candidate.url)
                        score = score_candidate(candidate)
                        if score.intent and score.service_fit:
                            plausible_count += 1
                        if not score.qualified:
                            continue
                        opportunity = candidate_to_opportunity(
                            ScoutCandidate(candidate.source.name, candidate.title, candidate.text, candidate.url),
                            scout=candidate.source.scout,
                        )
                        if opportunity is None:
                            continue
                        self.store.upsert(opportunity)
                        row = opportunity.to_row()
                        row["buyer_score"] = score.as_dict()
                        row["published_at"] = candidate.published_at or None
                        row["discovery_source"] = candidate.source.name
                        qualified.append(row)
                        qualified_channels.add(candidate.source.scout)
                except Exception as exc:
                    errors.append({"source": source.name, "error": str(exc)[:240]})

        qualified.sort(
            key=lambda row: (
                int((row.get("buyer_score") or {}).get("score") or 0),
                float(row.get("estimated_revenue") or 0),
            ),
            reverse=True,
        )
        qualified_count = len(qualified)
        return {
            "promoted": qualified[:50],
            "promoted_count": qualified_count,
            "errors": errors,
            "outbound_enabled": False,
            "transaction_authority": False,
            "buyer_inventory": {
                "raw_candidates": raw_count,
                "deduplicated_candidates": len(seen_urls),
                "plausible_commercial": plausible_count,
                "qualified_buyers": qualified_count,
                "qualified_channel_count": len(qualified_channels),
                "source_count": len(selected_sources),
                "target_min_per_day": DAILY_TARGET_MIN,
                "target_max_per_day": DAILY_TARGET_MAX,
                "qualification_threshold": QUALIFIED_BUYER_SCORE,
                "preferred_freshness_hours": PREFERRED_FRESHNESS_HOURS,
                "maximum_freshness_hours": MAX_FRESHNESS_HOURS,
                "inventory_status": "target_met" if qualified_count >= DAILY_TARGET_MIN else "source_shortage",
            },
        }
