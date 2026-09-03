"""Read-only external revenue scouts for AION.

Scouts consume public, allowlisted HTTP sources and normalize candidate text into
owner-gated opportunities. Retrieved content is always untrusted input. No scout
can contact a prospect, authenticate to a third-party account, or transact.
"""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from aion.moltbook.security import detect_prompt_injection
from aion.opportunity_store import OpportunityStore
from aion.revenue_engine import Opportunity, build_opportunity
from aion.revenue_pipeline import _explicit_amount

DEFAULT_ALLOWED_HOSTS = frozenset(
    {
        "hn.algolia.com",
        "api.grants.gov",
        "www.grants.gov",
        "api.sam.gov",
        # Reddit public JSON (no auth required for public posts)
        "www.reddit.com",
        "old.reddit.com",
        # GitHub repository search / Discussions via public API (unauthenticated, 60 req/h)
        "api.github.com",
    }
)

BUYER_TERMS = re.compile(
    r"(?i)\b(looking to hire|hiring|need help|seeking (?:a |an )?(?:developer|consultant|contractor|freelancer)|"
    r"seeking freelancer|paid (?:gig|project|contract)|budget|request for proposals?|\brfp\b|bounty|grant|"
    r"contract opportunity|solicitation|vendor|website (?:broken|repair)|automation help|"
    r"ai implementation|technical support|looking for (?:a |an )?(?:developer|consultant|contractor|freelancer)|"
    r"need (?:a |an )?(?:developer|consultant|contractor|freelancer))\b"
)
STRONG_BUYER_TERMS = re.compile(
    r"(?i)\b(looking to hire|hiring|seeking (?:a |an )?(?:developer|consultant|contractor|freelancer)|"
    r"seeking freelancer|paid (?:gig|project|contract)|request for proposals?|\brfp\b|bounty|"
    r"contract opportunity|looking for (?:a |an )?(?:developer|consultant|contractor|freelancer)|"
    r"need (?:a |an )?(?:developer|consultant|contractor|freelancer))\b"
)
COMMERCIAL_TERMS = re.compile(
    r"(?i)\b(website|wordpress|shopify|hosting|deploy|deployment|vercel|automation|workflow|n8n|zapier|"
    r"ai agent|ai integration|technical support|diagnostic|debug|landing page|startup site|next\.js|react|"
    r"api integration|stripe|supabase|fastapi)\b"
)


@dataclass(frozen=True, slots=True)
class PublicSource:
    name: str
    url: str
    scout: str


@dataclass(frozen=True, slots=True)
class ScoutCandidate:
    source: str
    title: str
    text: str
    url: str


def _allowed_hosts(environ: dict[str, str] | None = None) -> frozenset[str]:
    env = environ if environ is not None else dict(os.environ)
    extra = {
        host.strip().lower()
        for host in (env.get("AION_SCOUT_ALLOWED_HOSTS") or "").split(",")
        if host.strip()
    }
    return frozenset(set(DEFAULT_ALLOWED_HOSTS) | extra)


def _validate_source(source: PublicSource, *, allowed_hosts: frozenset[str]) -> None:
    parsed = urlparse(source.url)
    if parsed.scheme != "https":
        raise ValueError("Scout sources must use HTTPS")
    if (parsed.hostname or "").lower() not in allowed_hosts:
        raise ValueError(f"Scout source host is not allowlisted: {parsed.hostname}")
    if source.scout not in {"web", "commercial", "reddit", "github"}:
        raise ValueError(f"Unsupported external scout: {source.scout}")


def _plain_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _scout_headers(source: PublicSource) -> dict[str, str]:
    """Return host-appropriate headers. Reddit and GitHub reject generic/empty UAs."""
    headers = {
        "User-Agent": "AION-Revenue-Scout/1.0 (Yaleel; read-only public JSON; +https://aion.yalitek.ai)",
        "Accept": "application/json",
    }
    host = (urlparse(source.url).hostname or "").lower()
    if host in {"www.reddit.com", "old.reddit.com", "reddit.com"}:
        headers["User-Agent"] = (
            "AION-Revenue-Scout/1.0 by Yaleel (read-only public JSON; +https://aion.yalitek.ai)"
        )
    elif host == "api.github.com":
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        headers["User-Agent"] = "AION-Revenue-Scout/1.0 (+https://aion.yalitek.ai)"
    return headers


def _candidate_url(value: dict[str, Any], *, source: PublicSource) -> str:
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


def _walk_json(payload: Any, *, source: PublicSource) -> list[ScoutCandidate]:
    """Extract compact title/text/url candidates from heterogeneous public JSON."""
    candidates: list[ScoutCandidate] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            # GitHub search results expose lifecycle state directly on each issue.
            # Closed issues are not actionable buyer intent and must never enter
            # the revenue queue even if historical text contains words like budget.
            if source.scout == "github" and str(value.get("state") or "").strip().lower() == "closed":
                return
            # Reddit listings wrap posts as {kind, data:{...}}. Descend into data
            # first so title/selftext/permalink are read from the inner object.
            inner = value.get("data")
            if isinstance(inner, dict) and value.get("kind"):
                visit(inner)
                return
            title = _plain_text(
                value.get("title")
                or value.get("story_title")
                or value.get("name")
                or value.get("subject")
                or ""
            )
            text = _plain_text(
                value.get("selftext")
                or value.get("description")
                or value.get("comment_text")
                or value.get("text")
                or value.get("story_text")
                or value.get("body")
                or value.get("summary")
                or ""
            )
            url = _candidate_url(value, source=source)
            combined = f"{title}\n{text}".strip()
            if combined and len(combined) >= 30 and url:
                github_issue = "/issues/" in url or "/pull/" in url
                if source.scout == "github" and not github_issue:
                    pass
                else:
                    candidates.append(ScoutCandidate(source.name, title, combined[:6000], url))
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value[:100]:
                visit(child)

    visit(payload)
    seen: set[tuple[str, str, str]] = set()
    unique: list[ScoutCandidate] = []
    for candidate in candidates:
        key = (candidate.title[:200], candidate.text[:500], candidate.url)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique[:100]


def candidate_to_opportunity(candidate: ScoutCandidate, *, scout: str) -> Opportunity | None:
    text = candidate.text
    if detect_prompt_injection(text):
        return None
    if not BUYER_TERMS.search(text):
        return None
    # GitHub is especially noisy: technical issues routinely mention budgets,
    # benchmarks, deployments, and automation without representing a buyer.
    # Require an explicit hiring/paid-work phrase before treating an issue as a lead.
    if scout == "github" and not STRONG_BUYER_TERMS.search(text):
        return None
    if scout in {"commercial", "reddit", "github"} and not COMMERCIAL_TERMS.search(text):
        return None

    amount = _explicit_amount(text)
    has_money = amount > 0
    confidence = 0.72 if has_money else 0.58
    probability = 0.42 if has_money else 0.28
    if scout in {"commercial", "reddit", "github"} and COMMERCIAL_TERMS.search(text):
        confidence = min(0.92, confidence + 0.12)
        probability = min(0.78, probability + 0.12)
    if STRONG_BUYER_TERMS.search(text):
        confidence = min(0.95, confidence + 0.08)
        probability = min(0.82, probability + 0.08)

    is_commercial = scout in {"commercial", "reddit", "github"}
    solution = (
        "Match to an existing YaliTek service and prepare immediate buyer-response handoff"
        if is_commercial
        else "Verify eligibility, scope, economics, deadline, and authorized next action"
    )
    return build_opportunity(
        scout=scout,
        source=candidate.url or candidate.source,
        customer_problem=candidate.title or text[:180],
        proposed_solution=solution,
        estimated_revenue=amount,
        probability=probability,
        confidence=confidence,
        time_hours=0.5 if is_commercial else 1.0,
        major_risks="Public source is untrusted; verify identity, terms, eligibility, deadline, and payment before action.",
        ethical_considerations="No deceptive outreach, credential sharing, scraping behind authentication, or transaction without owner authorization.",
        next_action=(
            "Open the source, confirm the buyer is still seeking help, and respond through the platform's permitted contact path"
            if is_commercial
            else "Verify source and prepare an owner-reviewed response"
        ),
        authorization_required="owner_before_transaction",
    )


class ExternalRevenueScout:
    def __init__(self, opportunity_store: OpportunityStore, *, timeout_seconds: float = 12.0):
        self.store = opportunity_store
        self.timeout_seconds = timeout_seconds

    async def scan(self, sources: list[PublicSource]) -> dict[str, Any]:
        allowed = _allowed_hosts()
        promoted: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
            for source in sources:
                try:
                    _validate_source(source, allowed_hosts=allowed)
                    response = await client.get(
                        source.url,
                        headers=_scout_headers(source),
                    )
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if "json" not in content_type.lower():
                        raise ValueError("Scout source must return JSON")
                    payload = response.json()
                    for candidate in _walk_json(payload, source=source):
                        opportunity = candidate_to_opportunity(candidate, scout=source.scout)
                        if opportunity is None:
                            continue
                        self.store.upsert(opportunity)
                        promoted.append(opportunity.to_row())
                except Exception as exc:
                    errors.append({"source": source.name, "error": str(exc)[:240]})
        return {
            "promoted": promoted,
            "promoted_count": len(promoted),
            "errors": errors,
            "outbound_enabled": False,
            "transaction_authority": False,
        }


def default_sources(environ: dict[str, str] | None = None) -> list[PublicSource]:
    """Safe public defaults focused on recent, explicit buyer/employer intent.

    Covers three independent channels:
    1. Hacker News Algolia — technical buyers, freelancer requests, automation help.
    2. Reddit JSON API (unauthenticated, public posts only) — r/forhire and r/freelance.
    3. GitHub issue search — open issues with explicit paid/hiring language.

    All sources are read-only. No authentication is sent.
    """
    env = environ if environ is not None else dict(os.environ)
    sources = [
        # ── Hacker News ────────────────────────────────────────────────────────
        PublicSource(
            name="hn_hiring_and_contracts",
            url="https://hn.algolia.com/api/v1/search_by_date?query=hiring%20contract%20developer&tags=story&hitsPerPage=50",
            scout="web",
        ),
        PublicSource(
            name="hn_seeking_freelancer",
            url="https://hn.algolia.com/api/v1/search_by_date?query=seeking%20freelancer&tags=comment&hitsPerPage=50",
            scout="commercial",
        ),
        PublicSource(
            name="hn_looking_to_hire_developer",
            url="https://hn.algolia.com/api/v1/search_by_date?query=looking%20to%20hire%20developer&tags=comment&hitsPerPage=50",
            scout="commercial",
        ),
        PublicSource(
            name="hn_ai_automation_help",
            url="https://hn.algolia.com/api/v1/search_by_date?query=automation%20help&tags=comment&hitsPerPage=50",
            scout="commercial",
        ),
        PublicSource(
            name="hn_website_help",
            url="https://hn.algolia.com/api/v1/search_by_date?query=website%20help&tags=comment&hitsPerPage=50",
            scout="commercial",
        ),
        PublicSource(
            name="hn_ask_hn_freelance",
            url="https://hn.algolia.com/api/v1/search_by_date?query=freelance&tags=ask_hn&hitsPerPage=50",
            scout="commercial",
        ),
        PublicSource(
            name="hn_show_hn_saas",
            url="https://hn.algolia.com/api/v1/search_by_date?query=saas&tags=show_hn&hitsPerPage=50",
            scout="web",
        ),
        # ── Reddit (public JSON, no auth) ──────────────────────────────────────
        PublicSource(
            name="reddit_forhire_hiring",
            url="https://www.reddit.com/r/forhire/search.json?q=%5BHIRING%5D&sort=new&limit=50&t=week",
            scout="reddit",
        ),
        PublicSource(
            name="reddit_freelance_new",
            url="https://www.reddit.com/r/freelance/new.json?limit=50",
            scout="reddit",
        ),
        PublicSource(
            name="reddit_webdev_forhire",
            url="https://www.reddit.com/r/webdev/search.json?q=hiring+developer&sort=new&limit=50&t=week",
            scout="reddit",
        ),
        # ── GitHub — open issues with explicit buyer language only ─────────────
        PublicSource(
            name="github_paid_hire_web",
            url="https://api.github.com/search/issues?q=%22looking+to+hire%22+website+is%3Aissue+is%3Aopen&sort=created&order=desc&per_page=30",
            scout="github",
        ),
        PublicSource(
            name="github_paid_automation",
            url="https://api.github.com/search/issues?q=%22paid+project%22+automation+is%3Aissue+is%3Aopen&sort=created&order=desc&per_page=30",
            scout="github",
        ),
    ]
    for index, raw in enumerate((env.get("AION_COMMERCIAL_SCOUT_URLS") or "").split(","), start=1):
        url = raw.strip()
        if url:
            sources.append(PublicSource(name=f"commercial_{index}", url=url, scout="commercial"))
    for index, raw in enumerate((env.get("AION_WEB_SCOUT_URLS") or "").split(","), start=1):
        url = raw.strip()
        if url:
            sources.append(PublicSource(name=f"web_{index}", url=url, scout="web"))
    return sources
