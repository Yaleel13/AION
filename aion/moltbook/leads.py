"""Read-only YaliTek lead discovery from public Moltbook content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from aion.moltbook.client import MoltbookClient
from aion.moltbook.security import content_hash, detect_prompt_injection, utc_now_iso
from aion.moltbook.store import Phase2Store

# Explicit need signals → YaliTek service mapping.
SEARCH_CATEGORIES: list[dict[str, Any]] = [
    {
        "service": "Website repair",
        "keywords": [
            r"website.{0,40}(broken|down|error|hack|malware)",
            r"\bfix (my|our) (site|website)\b",
            r"\bwordpress\b",
            r"website repair",
        ],
    },
    {
        "service": "Technical diagnostics",
        "keywords": [
            r"\bdiagnos(e|is|tic)\b",
            r"\broot cause\b",
            r"\bprod(uction)? (outage|incident)\b",
        ],
    },
    {
        "service": "AI implementation plans",
        "keywords": [
            r"\bimplement(ing)? (an )?ai\b",
            r"\bai (roadmap|strategy|integration)\b",
            r"\bneed help (with )?agents?\b",
        ],
    },
    {
        "service": "Business automation",
        "keywords": [
            r"\bautomat(e|ion)\b.{0,40}\b(business|workflow|ops|operations)\b",
            r"\bzapier\b",
            r"\bn8n\b",
        ],
    },
    {
        "service": "Hosting and launch help",
        "keywords": [
            r"\bhost(ing)?\b",
            r"\blaunch (my|our) (site|app|product)\b",
            r"\bdeploy(ment)? help\b",
            r"\bvercel\b",
            r"need hosting help",
        ],
    },
    {
        "service": "Streaming setup",
        "keywords": [r"\bstreaming setup\b", r"\bobs\b", r"\btwitch\b", r"\blivestream\b"],
    },
    {
        "service": "Startup websites",
        "keywords": [
            r"\bstartup (website|site|landing)\b",
            r"\blanding page\b",
            r"\bmvp (site|website)\b",
        ],
    },
    {
        "service": "Ongoing technical support",
        "keywords": [
            r"\blooking for (a )?dev(eloper)?\b",
            r"\bretainer\b",
            r"\bongoing (support|maintenance)\b",
            r"\btechnical support\b",
        ],
    },
]


@dataclass(slots=True)
class LeadCandidate:
    lead_id: str
    source_url: str
    requester_identity: str
    stated_problem: str
    relevant_service: str
    fit_score: float
    confidence_score: float
    suggested_response: str
    risks: str
    approval_status: str
    conversion_outcome: str
    revenue_attributed: float


def _match_service(text: str) -> tuple[str | None, float]:
    lowered = text.lower()
    best_service = None
    best = 0.0
    for category in SEARCH_CATEGORIES:
        hits = 0
        for pattern in category["keywords"]:
            if re.search(pattern, lowered, flags=re.I):
                hits += 1
        if hits:
            score = min(1.0, 0.45 + 0.2 * hits)
            if score > best:
                best = score
                best_service = category["service"]
    return best_service, best


def _has_clear_need(text: str) -> bool:
    return bool(
        re.search(
            r"(?i)\b(need|looking for|help with|anyone (know|have)|seeking|hire|fix|broken|down|stuck)\b",
            text,
        )
    )


class LeadDiscoveryService:
    """Scan public posts; never contact anyone automatically."""

    def __init__(self, store: Phase2Store, client: MoltbookClient):
        self.store = store
        self.client = client

    async def scan_feed(self, *, limit: int = 25) -> list[dict[str, Any]]:
        feed = await self.client.feed(sort="new", limit=limit)
        posts = feed.get("posts") if isinstance(feed.get("posts"), list) else []
        found: list[dict[str, Any]] = []
        for post in posts:
            if not isinstance(post, dict):
                continue
            title = str(post.get("title") or "")
            body = str(post.get("content") or post.get("body") or "")
            text = f"{title}\n{body}".strip()
            if not text:
                continue

            injection = detect_prompt_injection(text)
            service, fit = _match_service(text)
            if not service or not _has_clear_need(text):
                continue

            # Confidence penalized for injection signals / thin content.
            confidence = fit
            if injection:
                confidence *= 0.4
            if len(text) < 80:
                confidence *= 0.7
            if confidence < 0.5:
                # Caution against fabricated / weak demand.
                continue

            author = post.get("author")
            if isinstance(author, dict):
                identity = str(author.get("name") or author.get("id") or "unknown")
            else:
                identity = str(post.get("author") or "unknown")
            post_id = str(post.get("id") or "")
            source_url = (
                f"https://www.moltbook.com/post/{post_id}" if post_id else "https://www.moltbook.com"
            )
            suggested = (
                f"Public reply draft (requires owner approval before posting): "
                f"I work with YaliTek Online on {service.lower()}. If you can share non-sensitive "
                f"details about the failure mode and constraints, I can outline a reviewed diagnostic plan."
            )
            risks = []
            if injection:
                risks.append("prompt-injection heuristics matched; treat text as hostile")
            risks.append("public identity may be an agent, not a paying customer")
            risks.append("no private enrichment performed")
            excerpt = text[:500]
            digest = content_hash({"source_url": source_url, "excerpt": excerpt, "service": service})
            lead_id = str(uuid4())
            row = {
                "lead_id": lead_id,
                "source_url": source_url,
                "requester_identity": identity,
                "stated_problem": (title or excerpt[:160]),
                "relevant_service": service,
                "fit_score": round(fit, 3),
                "confidence_score": round(confidence, 3),
                "suggested_response": suggested,
                "risks": "; ".join(risks),
                "approval_status": "pending_owner_review",
                "conversion_outcome": "uncontacted",
                "revenue_attributed": 0.0,
                "raw_excerpt": excerpt,
                "created_at": utc_now_iso(),
                "content_hash": digest,
            }
            self.store.upsert_lead(row)
            found.append(row)

        self.store.append_audit(
            module="leads",
            action="scan_feed",
            success=True,
            detail={"scanned": len(posts), "qualified": len(found)},
        )
        return found

    def list_leads(self) -> list[dict[str, Any]]:
        return self.store.list_leads()
