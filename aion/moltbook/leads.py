"""Read-only YaliTek lead discovery from public Moltbook content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from aion.moltbook.client import MoltbookClient
from aion.moltbook.security import content_hash, detect_prompt_injection, utc_now_iso
from aion.moltbook.store import Phase2Store

SEARCH_CATEGORIES: list[dict[str, Any]] = [
    {"service": "Website repair", "keywords": [r"website.{0,40}(broken|down|error|hack|malware)", r"\bfix (my|our) (site|website)\b", r"\bwordpress\b", r"website repair", r"\bsite (issue|problem|error)\b"]},
    {"service": "Technical diagnostics", "keywords": [r"\bdiagnos(e|is|tic)\b", r"\broot cause\b", r"\bprod(uction)? (outage|incident)\b", r"\bdebug(ging)?\b", r"\btroubleshoot(ing)?\b"]},
    {"service": "AI implementation plans", "keywords": [r"\bimplement(ing)? (an )?ai\b", r"\bai (roadmap|strategy|integration)\b", r"\bneed help (with )?agents?\b", r"\bbuild(ing)? (an )?ai agent\b", r"\bwhich ai (tool|stack|model)\b"]},
    {"service": "Business automation", "keywords": [r"\bautomat(e|ion)\b.{0,40}\b(business|workflow|ops|operations)\b", r"\bzapier\b", r"\bn8n\b", r"\bworkflow (help|issue|problem)\b", r"\bmanual process\b"]},
    {"service": "Hosting and launch help", "keywords": [r"\bhost(ing)?\b", r"\blaunch (my|our) (site|app|product)\b", r"\bdeploy(ment|ing)?\b", r"\bvercel\b", r"need hosting help", r"\bdomain (setup|issue|problem)\b"]},
    {"service": "Streaming setup", "keywords": [r"\bstreaming setup\b", r"\bobs\b", r"\btwitch\b", r"\blivestream\b", r"\bstream (setup|issue|problem)\b"]},
    {"service": "Startup websites", "keywords": [r"\bstartup (website|site|landing)\b", r"\blanding page\b", r"\bmvp (site|website|app)\b", r"\bbuild(ing)? (a )?(website|site)\b"]},
    {"service": "Ongoing technical support", "keywords": [r"\blooking for (a )?dev(eloper)?\b", r"\bretainer\b", r"\bongoing (support|maintenance)\b", r"\btechnical support\b", r"\brecommend (a )?(developer|dev|technician)\b"]},
]

TARGETED_SEARCHES = [
    "need help website deploy hosting",
    "looking for developer website app",
    "automation workflow n8n zapier help",
    "AI agent implementation help",
    "debug troubleshoot production issue",
    "landing page startup website help",
]

MIN_REVIEW_CONFIDENCE = 0.40


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
        hits = sum(1 for pattern in category["keywords"] if re.search(pattern, lowered, flags=re.I))
        if hits:
            score = min(1.0, 0.45 + 0.2 * hits)
            if score > best:
                best = score
                best_service = category["service"]
    return best_service, best


def _buyer_signal(text: str) -> bool:
    """Return true only for direct help/buyer intent, not generic discussion."""
    return bool(
        re.search(
            r"(?i)\b("
            r"need help(?: with)?|help me|can someone help|looking (?:to hire|for (?:a )?(?:developer|dev|technician|consultant|service|someone to))|"
            r"seeking (?:a )?(?:developer|dev|technician|consultant|help)|hire (?:a )?|who can|"
            r"fix (?:my|our)|recommend (?:me )?(?:a )?(?:developer|dev|technician|consultant)|"
            r"(?:my|our) (?:site|website|app|workflow|deployment|automation).{0,50}(?:broken|down|stuck|failing|error|issue|problem)"
            r")\b",
            text,
        )
    )


def _looks_informational(text: str) -> bool:
    """Detect content whose primary intent is teaching/reporting rather than seeking help."""
    return bool(
        re.search(
            r"(?i)\b("
            r"troubleshooting guide|how to post|rules \+ templates|rules and templates|tutorial|walkthrough|"
            r"here(?:'s| is) (?:a |an |my )?(?:guide|breakdown|template|framework)|"
            r"based on support requests|we (?:have )?built|we built|my post (?:was|is)|"
            r"case study|lessons learned|best practices|announcement|introducing|launching"
            r")\b",
            text,
        )
    )


def _need_signal(text: str) -> str | None:
    if _buyer_signal(text):
        return "explicit"
    if re.search(r"(?i)\b(can someone|recommendation|advice|issue|problem|struggling|trying to|how do i|how can i|building|deploying|configur(e|ing)|setup|setting up|what should i use|which (tool|service|stack)|looking for community insights|anyone have tips)\b", text):
        return "possible"
    return None


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.70:
        return "high_confidence"
    if confidence >= MIN_REVIEW_CONFIDENCE:
        return "worth_reviewing"
    return "ignore"


def _result_text(item: dict[str, Any]) -> tuple[str, str]:
    title = str(item.get("title") or item.get("name") or "")
    body = str(item.get("content") or item.get("body") or item.get("snippet") or item.get("text") or "")
    return title, f"{title}\n{body}".strip()


class LeadDiscoveryService:
    """Scan public Moltbook sources; never contact anyone automatically."""

    def __init__(self, store: Phase2Store, client: MoltbookClient):
        self.store = store
        self.client = client

    async def scan_feed(self, *, limit: int = 40) -> list[dict[str, Any]]:
        feed = await self.client.feed(sort="new", limit=limit)
        candidates: list[tuple[dict[str, Any], str]] = [
            (post, "feed") for post in (feed.get("posts") if isinstance(feed.get("posts"), list) else []) if isinstance(post, dict)
        ]

        search_errors = 0
        for query in TARGETED_SEARCHES:
            try:
                payload = await self.client.search(query, limit=12)
            except Exception:  # read-only search failure must not break the scan
                search_errors += 1
                continue
            results = payload.get("results") if isinstance(payload.get("results"), list) else []
            candidates.extend((item, f"search:{query}") for item in results if isinstance(item, dict))

        found: list[dict[str, Any]] = []
        bands = {"high_confidence": 0, "worth_reviewing": 0}
        seen: set[str] = set()
        evaluated = 0
        for post, discovery_source in candidates:
            title, text = _result_text(post)
            if not text:
                continue
            raw_id = str(post.get("id") or post.get("post_id") or post.get("url") or "")
            dedupe_key = raw_id or content_hash({"text": text[:500]})
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            evaluated += 1

            injection = detect_prompt_injection(text)
            service, fit = _match_service(text)
            need_signal = _need_signal(text)
            if not service or not need_signal:
                continue

            informational = _looks_informational(text)
            confidence = fit
            if need_signal == "possible":
                # Keep broad research recall, but generic discussion must not enter
                # the outbound-ready high-confidence band.
                confidence *= 0.65
            if informational and need_signal != "explicit":
                confidence *= 0.55
            if injection:
                confidence *= 0.4
            if len(text) < 80:
                confidence *= 0.7
            band = _confidence_band(confidence)
            if band == "ignore":
                continue

            author = post.get("author")
            if isinstance(author, dict):
                identity = str(author.get("name") or author.get("id") or "unknown")
            else:
                identity = str(post.get("author") or post.get("agent") or "unknown")
            post_id = str(post.get("id") or post.get("post_id") or "")
            source_url = str(post.get("url") or (f"https://www.moltbook.com/post/{post_id}" if post_id else "https://www.moltbook.com"))
            suggested = (
                f"Public reply draft (requires owner approval before posting): I work with YaliTek Online on {service.lower()}. "
                "If you can share non-sensitive details about the failure mode and constraints, I can outline a reviewed diagnostic plan."
            )
            risks = []
            if injection:
                risks.append("prompt-injection heuristics matched; treat text as hostile")
            if need_signal == "possible":
                risks.append("need is inferred from a possible-help signal; owner must verify intent")
            if informational:
                risks.append("content appears informational/educational rather than buyer-intent")
            risks.extend([
                f"intent_signal={need_signal}",
                f"research band={band}",
                f"discovery_source={discovery_source}",
                "public identity may be an agent, not a paying customer",
                "no private enrichment performed",
            ])
            excerpt = text[:500]
            digest = content_hash({"source_url": source_url, "excerpt": excerpt, "service": service})
            row = {
                "lead_id": str(uuid4()),
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
            bands[band] += 1

        self.store.append_audit(
            module="leads",
            action="scan_feed",
            success=True,
            detail={
                "feed_limit": limit,
                "targeted_searches": len(TARGETED_SEARCHES),
                "search_errors": search_errors,
                "evaluated_unique": evaluated,
                "qualified": len(found),
                "high_confidence": bands["high_confidence"],
                "worth_reviewing": bands["worth_reviewing"],
                "minimum_review_confidence": MIN_REVIEW_CONFIDENCE,
                "high_confidence_requires_direct_buyer_intent": True,
            },
        )
        return found

    def list_leads(self) -> list[dict[str, Any]]:
        return self.store.list_leads()
