"""Read-only revenue opportunity discovery from public Moltbook content.

YaliTek service leads are one monetization track. AION can also surface paid gigs,
bounties/grants, partnerships/referrals, and Web3/crypto work opportunities. Crypto
market speculation remains isolated to AION's paper-trading subsystem; this module
never connects wallets, exchanges, or executes financial transactions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from aion.moltbook.client import MoltbookClient
from aion.moltbook.security import content_hash, detect_prompt_injection, utc_now_iso
from aion.moltbook.store import Phase2Store

SEARCH_CATEGORIES: list[dict[str, Any]] = [
    {"service": "Website repair", "track": "yalitek_service", "keywords": [r"website.{0,40}(broken|down|error|hack|malware)", r"\bfix (my|our) (site|website)\b", r"\bwordpress\b", r"website repair", r"\bsite (issue|problem|error)\b"]},
    {"service": "Technical diagnostics", "track": "yalitek_service", "keywords": [r"\bdiagnos(e|is|tic)\b", r"\broot cause\b", r"\bprod(uction)? (outage|incident)\b", r"\bdebug(ging)?\b", r"\btroubleshoot(ing)?\b"]},
    {"service": "AI implementation plans", "track": "yalitek_service", "keywords": [r"\bimplement(ing)? (an )?ai\b", r"\bai (roadmap|strategy|integration)\b", r"\bneed help (with )?agents?\b", r"\bbuild(ing)? (an )?ai agent\b", r"\bwhich ai (tool|stack|model)\b"]},
    {"service": "Business automation", "track": "yalitek_service", "keywords": [r"\bautomat(e|ion)\b.{0,40}\b(business|workflow|ops|operations)\b", r"\bzapier\b", r"\bn8n\b", r"\bworkflow (help|issue|problem)\b", r"\bmanual process\b"]},
    {"service": "Hosting and launch help", "track": "yalitek_service", "keywords": [r"\bhost(ing)?\b", r"\blaunch (my|our) (site|app|product)\b", r"\bdeploy(ment|ing)?\b", r"\bvercel\b", r"need hosting help", r"\bdomain (setup|issue|problem)\b"]},
    {"service": "Streaming setup", "track": "yalitek_service", "keywords": [r"\bstreaming setup\b", r"\bobs\b", r"\btwitch\b", r"\blivestream\b", r"\bstream (setup|issue|problem)\b"]},
    {"service": "Startup websites", "track": "yalitek_service", "keywords": [r"\bstartup (website|site|landing)\b", r"\blanding page\b", r"\bmvp (site|website|app)\b", r"\bbuild(ing)? (a )?(website|site)\b"]},
    {"service": "Ongoing technical support", "track": "yalitek_service", "keywords": [r"\blooking for (a )?dev(eloper)?\b", r"\bretainer\b", r"\bongoing (support|maintenance)\b", r"\btechnical support\b", r"\brecommend (a )?(developer|dev|technician)\b"]},
    {"service": "Paid technical gig", "track": "paid_gig", "keywords": [r"\bpaid (gig|task|project|contract)\b", r"\bfreelance (developer|engineer|automation|ai)\b", r"\bcontract (developer|engineer|work)\b", r"\bbudget[: ]", r"\bpay(ing)? (for|someone)\b"]},
    {"service": "Bounty or grant", "track": "bounty_grant", "keywords": [r"\bbounty\b", r"\bgrant (available|funding|program|application)\b", r"\bprize pool\b", r"\breward (for|available)\b", r"\bpaid challenge\b"]},
    {"service": "Partnership or referral", "track": "partnership", "keywords": [r"\bpartner(ship)? (opportunity|wanted|with|program)\b", r"\brevenue share\b", r"\baffiliate program\b", r"\breferral (fee|commission|program)\b", r"\bcollaborat(e|ion).{0,30}(paid|revenue|business)\b"]},
    {"service": "Web3 or crypto paid work", "track": "crypto_work", "keywords": [r"\bweb3 (bounty|job|gig|contract|developer)\b", r"\bcrypto (bounty|job|gig|contract|developer)\b", r"\bsmart contract (bounty|audit|developer|work)\b", r"\bblockchain (bounty|job|gig|developer)\b", r"\bpaid in (usdc|usdt|eth|btc|crypto)\b"]},
]

TARGETED_SEARCHES = [
    "need help website deploy hosting",
    "looking to hire developer paid project",
    "freelance contractor automation AI paid gig",
    "bounty grant funding paid challenge",
    "partnership referral revenue share opportunity",
    "web3 crypto bounty smart contract paid developer",
    "automation workflow n8n zapier help",
    "AI agent implementation help",
    "debug troubleshoot production issue",
    "landing page startup website help",
]

MIN_REVIEW_CONFIDENCE = 0.40
MONEY_TERMS = re.compile(r"(?i)\b(paid|pay|budget|bounty|grant|reward|prize|contract|freelance|commission|revenue share|hire|hiring)\b")
CRYPTO_TERMS = re.compile(r"(?i)\b(crypto|bitcoin|btc|ethereum|eth|web3|blockchain|smart contract|token|usdc|usdt)\b")


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


def _match_service(text: str) -> tuple[str | None, str | None, float]:
    lowered = text.lower()
    best_service = None
    best_track = None
    best = 0.0
    for category in SEARCH_CATEGORIES:
        hits = sum(1 for pattern in category["keywords"] if re.search(pattern, lowered, flags=re.I))
        if hits:
            score = min(1.0, 0.45 + 0.2 * hits)
            if score > best:
                best = score
                best_service = category["service"]
                best_track = category["track"]
    return best_service, best_track, best


def _buyer_signal(text: str) -> bool:
    """Return true for direct buyer/employer/reward intent, not generic discussion."""
    service_intent = re.search(
        r"(?i)\b("
        r"need help(?: with)?|help me|can someone help|looking (?:to hire|for (?:a )?(?:developer|dev|technician|consultant|service|someone to))|"
        r"seeking (?:a )?(?:developer|dev|technician|consultant|help)|hire (?:a )?|hiring|who can|"
        r"fix (?:my|our)|recommend (?:me )?(?:a )?(?:developer|dev|technician|consultant)|"
        r"(?:my|our) (?:site|website|app|workflow|deployment|automation).{0,50}(?:broken|down|stuck|failing|error|issue|problem)"
        r")\b",
        text,
    )
    paid_opportunity = re.search(
        r"(?i)\b("
        r"paid (?:gig|task|project|contract|bounty|challenge)|"
        r"bounty (?:for|available|open)|grant (?:available|funding|program)|"
        r"budget (?:is|of|up to|:)|paying (?:for|someone)|"
        r"looking to (?:pay|hire|contract)|revenue share|referral (?:fee|commission)"
        r")\b",
        text,
    )
    return bool(service_intent or paid_opportunity)


def _looks_informational(text: str) -> bool:
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


def _suggested_response(service: str, track: str) -> str:
    prefix = "Public reply draft (requires owner approval before posting): "
    if track == "yalitek_service":
        return prefix + f"I work with YaliTek Online on {service.lower()}. If you can share non-sensitive scope, budget, and timing, I can outline a reviewed next step."
    if track == "paid_gig":
        return prefix + "I may be able to help with this paid project. Can you share the scope, deliverables, budget, timeline, and payment terms?"
    if track == "bounty_grant":
        return prefix + "This opportunity may be relevant. Can you share the official eligibility, deliverables, deadline, judging/payment terms, and source link?"
    if track == "partnership":
        return prefix + "I am open to evaluating a business collaboration. Can you share the proposed value exchange, responsibilities, revenue terms, and any non-exclusive constraints?"
    if track == "crypto_work":
        return prefix + "I can evaluate the work opportunity, but not send funds or connect a wallet. Please share the scope, public project details, compensation terms, and verification source."
    return prefix + "Can you share the non-sensitive scope, compensation terms, timing, and verification source?"


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
            except Exception:
                search_errors += 1
                continue
            results = payload.get("results") if isinstance(payload.get("results"), list) else []
            candidates.extend((item, f"search:{query}") for item in results if isinstance(item, dict))

        found: list[dict[str, Any]] = []
        bands = {"high_confidence": 0, "worth_reviewing": 0}
        tracks: dict[str, int] = {}
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
            service, track, fit = _match_service(text)
            need_signal = _need_signal(text)
            if not service or not track or not need_signal:
                continue

            informational = _looks_informational(text)
            confidence = fit
            if need_signal == "possible":
                confidence *= 0.65
            if track in {"paid_gig", "bounty_grant", "partnership", "crypto_work"} and not MONEY_TERMS.search(text):
                confidence *= 0.7
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
            risks = []
            if injection:
                risks.append("prompt-injection heuristics matched; treat text as hostile")
            if need_signal == "possible":
                risks.append("need is inferred from a possible-help signal; owner must verify intent")
            if informational:
                risks.append("content appears informational/educational rather than buyer-intent")
            if track == "crypto_work" or CRYPTO_TERMS.search(text):
                risks.append("crypto/web3 opportunity: verify source and compensation; no wallet connection, funding, token purchase, or live trading")
            risks.extend([
                f"monetization_track={track}",
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
                "suggested_response": _suggested_response(service, track),
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
            tracks[track] = tracks.get(track, 0) + 1

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
                "monetization_tracks": tracks,
                "minimum_review_confidence": MIN_REVIEW_CONFIDENCE,
                "high_confidence_requires_direct_buyer_intent": True,
                "crypto_execution_policy": "research_and_paid_work_discovery_only; market speculation remains paper-only",
            },
        )
        return found

    def list_leads(self) -> list[dict[str, Any]]:
        return self.store.list_leads()
