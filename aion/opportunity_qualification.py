"""Evidence-based opportunity qualification for AION Revenue Engine.

This module decides whether a discovered opportunity is worth pursuing based on
known capability fit, eligibility evidence, effort, urgency, and expected net
value. Unknown facts remain explicitly unknown and cannot be upgraded to verified.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

CAPABILITY_TERMS = {
    "website": ("website", "wordpress", "landing page", "web development", "site repair"),
    "hosting": ("hosting", "deployment", "deploy", "vercel", "domain"),
    "automation": ("automation", "workflow", "n8n", "zapier", "business process"),
    "ai": ("artificial intelligence", "ai agent", "ai integration", "openai", "llm"),
    "diagnostics": ("diagnostic", "debug", "troubleshoot", "technical support", "incident"),
    "streaming": ("streaming", "obs", "livestream", "twitch"),
}

DEFAULT_CAPABILITIES = frozenset(CAPABILITY_TERMS.keys())

_DEADLINE_PATTERNS = [
    re.compile(r"(?i)\b(?:close|closing|deadline|due)\s*(?:date)?\s*[:=-]?\s*(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"(?i)\b(?:close|closing|deadline|due)\s*(?:date)?\s*[:=-]?\s*(\d{1,2}/\d{1,2}/\d{4})\b"),
]


@dataclass(frozen=True, slots=True)
class Qualification:
    opportunity_id: str
    capability_fit: float
    capability_matches: list[str]
    eligibility_status: str
    eligibility_evidence: list[str]
    deadline_status: str
    days_remaining: int | None
    effort_hours: float
    estimated_net_value: float
    pursue_score: float
    recommendation: str
    blockers: list[str]
    unknowns: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _configured_capabilities(environ: dict[str, str] | None = None) -> frozenset[str]:
    env = environ if environ is not None else dict(os.environ)
    raw = (env.get("AION_YALITEK_CAPABILITIES") or "").strip()
    if not raw:
        return DEFAULT_CAPABILITIES
    allowed = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return frozenset(item for item in allowed if item in CAPABILITY_TERMS)


def _capability_fit(text: str, capabilities: frozenset[str]) -> tuple[float, list[str]]:
    lowered = text.lower()
    matched = []
    for capability in capabilities:
        terms = CAPABILITY_TERMS.get(capability, ())
        if any(term in lowered for term in terms):
            matched.append(capability)
    if not matched:
        return 0.0, []
    return min(1.0, 0.45 + 0.15 * len(matched)), sorted(matched)


def _eligibility(text: str, environ: dict[str, str] | None = None) -> tuple[str, list[str], list[str]]:
    env = environ if environ is not None else dict(os.environ)
    evidence: list[str] = []
    unknowns: list[str] = []
    lowered = text.lower()

    # Positive assertions must come from authenticated owner configuration, never inferred.
    sam_registered = (env.get("AION_SAM_REGISTERED") or "").strip().lower()
    if sam_registered in {"1", "true", "yes", "on"}:
        evidence.append("owner-configured SAM registration=true")
    elif "sam.gov" in lowered or "federal contract" in lowered:
        unknowns.append("SAM registration status")

    small_business = (env.get("AION_SMALL_BUSINESS_VERIFIED") or "").strip().lower()
    if small_business in {"1", "true", "yes", "on"}:
        evidence.append("owner-configured small-business status=true")
    elif "small business" in lowered or "set-aside" in lowered:
        unknowns.append("small-business/set-aside eligibility")

    grants_eligible = (env.get("AION_GRANT_ELIGIBILITY_VERIFIED") or "").strip().lower()
    if grants_eligible in {"1", "true", "yes", "on"}:
        evidence.append("owner-configured grant eligibility=true")
    elif "grant opportunity" in lowered:
        unknowns.append("grant applicant eligibility")

    if evidence and not unknowns:
        return "verified_for_known_requirements", evidence, unknowns
    if unknowns:
        return "unknown_requires_verification", evidence, unknowns
    return "not_required_or_not_detected", evidence, unknowns


def _deadline(text: str, now: datetime | None = None) -> tuple[str, int | None]:
    now = now or datetime.now(timezone.utc)
    for pattern in _DEADLINE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw = match.group(1)
        try:
            deadline = datetime.strptime(raw, "%Y-%m-%d" if "-" in raw else "%m/%d/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        days = (deadline.date() - now.date()).days
        if days < 0:
            return "expired", days
        if days <= 3:
            return "critical", days
        if days <= 14:
            return "soon", days
        return "open", days
    return "unknown", None


def qualify_opportunity(row: dict[str, Any], *, environ: dict[str, str] | None = None, now: datetime | None = None) -> Qualification:
    text = "\n".join(
        str(row.get(key) or "")
        for key in ("customer_problem", "proposed_solution", "major_risks", "ethical_considerations", "next_action", "source")
    )
    capabilities = _configured_capabilities(environ)
    capability_fit, matches = _capability_fit(text, capabilities)
    eligibility_status, evidence, unknowns = _eligibility(text, environ)
    deadline_status, days_remaining = _deadline(text, now)

    effort = max(0.5, float(row.get("time_hours") or 1.0))
    expected_value = max(0.0, float(row.get("expected_value") or 0.0))
    capital = max(0.0, float(row.get("capital_required") or 0.0))
    estimated_net = max(0.0, expected_value - capital)

    blockers: list[str] = []
    if deadline_status == "expired":
        blockers.append("deadline expired")
    if capability_fit <= 0.0:
        blockers.append("no verified capability match")
    if eligibility_status == "unknown_requires_verification":
        blockers.append("eligibility not verified")

    # Unknown revenue should not score like a known zero-value opportunity; it is research-only.
    revenue_known = float(row.get("estimated_revenue") or 0.0) > 0
    value_component = math.log1p(estimated_net) / 10.0 if revenue_known else 0.0
    urgency_bonus = {"critical": 0.08, "soon": 0.04, "open": 0.0, "unknown": -0.03, "expired": -1.0}[deadline_status]
    eligibility_factor = {
        "verified_for_known_requirements": 1.0,
        "not_required_or_not_detected": 0.85,
        "unknown_requires_verification": 0.45,
    }[eligibility_status]
    effort_factor = 1.0 / (1.0 + effort / 10.0)
    confidence = max(0.0, min(1.0, float(row.get("confidence") or 0.0)))
    probability = max(0.0, min(1.0, float(row.get("probability") or 0.0)))

    score = (0.32 * capability_fit + 0.24 * confidence + 0.18 * probability + 0.18 * min(1.0, value_component) + 0.08 * effort_factor)
    score *= eligibility_factor
    score += urgency_bonus
    score = max(0.0, min(1.0, score))

    if blockers and ("deadline expired" in blockers or "no verified capability match" in blockers):
        recommendation = "do_not_pursue"
    elif eligibility_status == "unknown_requires_verification" or not revenue_known:
        recommendation = "verify_before_pursuit"
    elif score >= 0.62:
        recommendation = "pursue_owner_review"
    elif score >= 0.42:
        recommendation = "watch_or_research"
    else:
        recommendation = "do_not_pursue"

    if not revenue_known:
        unknowns.append("commercial value/revenue")
    if deadline_status == "unknown":
        unknowns.append("deadline")

    return Qualification(
        opportunity_id=str(row.get("opportunity_id") or ""),
        capability_fit=round(capability_fit, 4),
        capability_matches=matches,
        eligibility_status=eligibility_status,
        eligibility_evidence=evidence,
        deadline_status=deadline_status,
        days_remaining=days_remaining,
        effort_hours=round(effort, 2),
        estimated_net_value=round(estimated_net, 2),
        pursue_score=round(score, 4),
        recommendation=recommendation,
        blockers=blockers,
        unknowns=sorted(set(unknowns)),
    )


def qualify_ranked(rows: list[dict[str, Any]], *, environ: dict[str, str] | None = None) -> list[dict[str, Any]]:
    qualified = []
    for row in rows:
        q = qualify_opportunity(row, environ=environ).as_dict()
        qualified.append({**row, "qualification": q})
    return sorted(qualified, key=lambda item: float(item["qualification"]["pursue_score"]), reverse=True)
