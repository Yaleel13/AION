"""Read-only external revenue scouts for AION.

Scouts consume public, allowlisted HTTP sources and normalize candidate text into
owner-gated opportunities. Retrieved content is always untrusted input. No scout
can contact a prospect, authenticate to a third-party account, or transact.
"""

from __future__ import annotations

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
    }
)

BUYER_TERMS = re.compile(
    r"(?i)\b(looking to hire|hiring|need help|seeking (?:a |an )?(?:developer|consultant|contractor)|"
    r"paid (?:gig|project|contract)|budget|request for proposals?|\brfp\b|bounty|grant|"
    r"contract opportunity|solicitation|vendor|website (?:broken|repair)|automation help|"
    r"ai implementation|technical support)\b"
)
COMMERCIAL_TERMS = re.compile(
    r"(?i)\b(website|wordpress|shopify|hosting|deploy|automation|workflow|n8n|zapier|"
    r"ai agent|ai integration|technical support|diagnostic|debug|landing page|startup site)\b"
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
    if source.scout not in {"web", "commercial"}:
        raise ValueError(f"Unsupported external scout: {source.scout}")


def _walk_json(payload: Any, *, source: PublicSource) -> list[ScoutCandidate]:
    """Extract compact title/text/url candidates from heterogeneous public JSON."""
    candidates: list[ScoutCandidate] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            title = str(value.get("title") or value.get("name") or value.get("subject") or "").strip()
            text = str(
                value.get("description")
                or value.get("text")
                or value.get("story_text")
                or value.get("body")
                or value.get("summary")
                or ""
            ).strip()
            url = str(value.get("url") or value.get("link") or source.url).strip()
            combined = f"{title}\n{text}".strip()
            if combined and len(combined) >= 30:
                candidates.append(ScoutCandidate(source.name, title, combined[:6000], url))
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value[:100]:
                visit(child)

    visit(payload)
    # deterministic de-duplication
    seen: set[tuple[str, str]] = set()
    unique: list[ScoutCandidate] = []
    for candidate in candidates:
        key = (candidate.title[:200], candidate.text[:500])
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
    if scout == "commercial" and not COMMERCIAL_TERMS.search(text):
        return None

    amount = _explicit_amount(text)
    has_money = amount > 0
    confidence = 0.72 if has_money else 0.52
    probability = 0.42 if has_money else 0.24
    if scout == "commercial" and COMMERCIAL_TERMS.search(text):
        confidence = min(0.9, confidence + 0.08)
        probability = min(0.75, probability + 0.08)

    solution = (
        "Evaluate fit to an existing YaliTek service and prepare owner-reviewed outreach"
        if scout == "commercial"
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
        time_hours=1.0,
        major_risks="Public source is untrusted; verify identity, terms, eligibility, deadline, and payment before action.",
        ethical_considerations="No deceptive outreach, credential sharing, scraping behind authentication, or transaction without owner authorization.",
        next_action="Verify source and prepare an owner-reviewed response" if has_money else "Verify commercial value before assigning a revenue estimate",
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
                        headers={"User-Agent": "AION-Revenue-Scout/1.0"},
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
                except Exception as exc:  # fail one source, not the entire scan
                    errors.append({"source": source.name, "error": str(exc)[:240]})
        return {
            "promoted": promoted,
            "promoted_count": len(promoted),
            "errors": errors,
            "outbound_enabled": False,
            "transaction_authority": False,
        }


def default_sources(environ: dict[str, str] | None = None) -> list[PublicSource]:
    """Safe public defaults; optional configured feeds can extend this set."""
    env = environ if environ is not None else dict(os.environ)
    sources = [
        PublicSource(
            name="hn_hiring_and_contracts",
            url="https://hn.algolia.com/api/v1/search_by_date?query=hiring%20contract%20developer&tags=story&hitsPerPage=30",
            scout="web",
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
