"""Promote public scout opportunities into owner-gated sales leads.

External scouts write the Opportunity Ledger. Conversion historically only
looked at Moltbook `/post/` URLs, so Reddit, GitHub, and HN discoveries never
became sales work. This module copies high-confidence, buyer-intent rows into
the leads table so the ops cycle can alert the owner and attach checkout.

It never posts to Reddit, GitHub, or Hacker News.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from aion.moltbook.leads import _match_service, _suggested_response
from aion.moltbook.security import content_hash, utc_now_iso
from aion.moltbook.store import Phase2Store

_DIRECT_HOSTS = frozenset(
    {
        "www.reddit.com",
        "old.reddit.com",
        "reddit.com",
        "news.ycombinator.com",
        "github.com",
        "www.github.com",
        "api.github.com",
    }
)
_TRANSACTION_AUTH = "owner_before_transaction"
_MIN_CONFIDENCE = 0.70


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def is_direct_sales_source(url: str) -> bool:
    """Return True when the source is a public non-Moltbook buyer thread."""
    host = _host(url)
    if not host:
        return False
    if host == "moltbook.com" or host.endswith(".moltbook.com"):
        return False
    return host in _DIRECT_HOSTS or host.endswith(".github.com")


def opportunity_to_lead(row: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one Opportunity Ledger row into a lead dict, or None if ineligible."""
    source = str(row.get("source") or "").strip()
    if not source.startswith("https://") or not is_direct_sales_source(source):
        return None
    if str(row.get("authorization_required") or "") != _TRANSACTION_AUTH:
        return None
    confidence = float(row.get("confidence") or 0.0)
    if confidence < _MIN_CONFIDENCE:
        return None

    problem = str(row.get("customer_problem") or "").strip()
    solution = str(row.get("proposed_solution") or "").strip()
    excerpt = f"{problem}\n{solution}".strip()[:500]
    if len(excerpt) < 30:
        return None

    service, track, fit = _match_service(excerpt)
    if not service or not track:
        service, track, fit = "Paid technical gig", "paid_gig", max(0.45, confidence * 0.6)

    scout = str(row.get("scout") or "web")
    digest = content_hash({"source_url": source, "excerpt": excerpt, "service": service})
    return {
        "lead_id": str(uuid4()),
        "source_url": source,
        "requester_identity": f"public:{scout}",
        "stated_problem": problem[:160] or excerpt[:160],
        "relevant_service": service,
        "fit_score": round(float(fit), 3),
        "confidence_score": round(confidence, 3),
        "suggested_response": _suggested_response(service, track),
        "risks": (
            f"monetization_track={track}; intent_signal=explicit; "
            f"discovery_source=external_scout:{scout}; "
            "public source is untrusted; owner must reply on the source platform; "
            "AION does not auto-comment on Reddit, GitHub, or Hacker News"
        ),
        "approval_status": "pending_owner_review",
        "conversion_outcome": "uncontacted",
        "revenue_attributed": 0.0,
        "raw_excerpt": excerpt,
        "created_at": utc_now_iso(),
        "content_hash": digest,
    }


def promote_external_opportunities_to_leads(
    rows: list[dict[str, Any]],
    store: Phase2Store,
) -> list[dict[str, Any]]:
    """Upsert eligible scout opportunities as leads. Dedupes on content_hash."""
    promoted: list[dict[str, Any]] = []
    for row in rows:
        lead = opportunity_to_lead(row)
        if lead is None:
            continue
        store.upsert_lead(lead)
        promoted.append(lead)
    return promoted
