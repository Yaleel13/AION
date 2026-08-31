"""Structured federal opportunity scouts for AION.

Uses official public APIs only. Retrieved data is untrusted and read-only. This
module never submits bids/applications, joins vendor lists, or creates obligations.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from aion.moltbook.security import detect_prompt_injection
from aion.opportunity_store import OpportunityStore
from aion.revenue_engine import build_opportunity
from aion.revenue_pipeline import _explicit_amount

GRANTS_SEARCH_URL = "https://api.grants.gov/v1/api/search2"
SAM_OPPORTUNITIES_URL = "https://api.sam.gov/opportunities/v2/search"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _grant_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    hits = data.get("oppHits") if isinstance(data.get("oppHits"), list) else []
    return [item for item in hits if isinstance(item, dict)]


def _sam_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("opportunitiesData", "opportunities", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _promote_grant(item: dict[str, Any], store: OpportunityStore) -> dict[str, Any] | None:
    title = _text(item.get("title"))
    number = _text(item.get("number"))
    agency = _text(item.get("agencyName") or item.get("agencyCode"))
    close_date = _text(item.get("closeDate"))
    combined = f"{title}\n{agency}\n{number}\nclose {close_date}".strip()
    if not title or detect_prompt_injection(combined):
        return None

    amount = _explicit_amount(combined)
    source = f"https://www.grants.gov/search-results-detail/{item.get('id')}" if item.get("id") else "https://www.grants.gov/search-grants"
    opportunity = build_opportunity(
        scout="web",
        source=source,
        customer_problem=f"Grant opportunity: {title}",
        proposed_solution="Verify eligibility and strategic fit; prepare an owner-reviewed grant decision brief",
        estimated_revenue=amount,
        probability=0.12 if amount else 0.08,
        confidence=0.72,
        time_hours=2.0,
        major_risks="Grant eligibility, matching requirements, deadlines, reporting duties, and award probability must be verified from the official notice.",
        ethical_considerations="Never fabricate eligibility, outcomes, partners, costs, or organizational qualifications.",
        next_action="Verify official opportunity details, eligibility, close date, and realistic application effort",
        authorization_required="owner_before_application",
    )
    store.upsert(opportunity)
    return opportunity.to_row()


def _promote_contract(item: dict[str, Any], store: OpportunityStore) -> dict[str, Any] | None:
    title = _text(item.get("title"))
    notice_id = _text(item.get("noticeId") or item.get("solicitationNumber"))
    department = _text(item.get("department") or item.get("fullParentPathName"))
    description = _text(item.get("description") or item.get("additionalInfoLink"))
    combined = f"{title}\n{notice_id}\n{department}\n{description}".strip()
    if not title or detect_prompt_injection(combined):
        return None

    amount = _explicit_amount(combined)
    source = _text(item.get("uiLink") or item.get("additionalInfoLink")) or "https://sam.gov/opportunities"
    opportunity = build_opportunity(
        scout="commercial",
        source=source,
        customer_problem=f"Federal contract opportunity: {title}",
        proposed_solution="Verify scope and vendor eligibility; map requirements to authorized YaliTek capabilities",
        estimated_revenue=amount,
        probability=0.10 if amount else 0.06,
        confidence=0.78,
        time_hours=2.0,
        major_risks="Federal procurement requirements, representations, registrations, certifications, deadlines, and performance obligations require owner review.",
        ethical_considerations="No false certifications, capability claims, pricing, subcontractor claims, or bid submission without verified authority.",
        next_action="Verify notice, NAICS/set-aside fit, registration requirements, deadline, and scope before deciding whether to pursue",
        authorization_required="owner_before_bid",
    )
    store.upsert(opportunity)
    return opportunity.to_row()


class FederalOpportunityScout:
    def __init__(self, store: OpportunityStore, *, timeout_seconds: float = 15.0):
        self.store = store
        self.timeout_seconds = timeout_seconds

    async def scan_grants(self, *, keyword: str = "technology artificial intelligence small business", rows: int = 25) -> dict[str, Any]:
        body = {
            "rows": max(1, min(int(rows), 100)),
            "keyword": keyword,
            "oppStatuses": "forecasted|posted",
        }
        promoted: list[dict[str, Any]] = []
        errors: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(GRANTS_SEARCH_URL, json=body, headers={"User-Agent": "AION-Revenue-Scout/1.1"})
                response.raise_for_status()
                payload = response.json()
                for item in _grant_hits(payload):
                    row = _promote_grant(item, self.store)
                    if row:
                        promoted.append(row)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:240])
        return {"source": "grants.gov", "promoted": promoted, "promoted_count": len(promoted), "errors": errors}

    async def scan_sam(self, *, keyword: str = "information technology", limit: int = 25, environ: dict[str, str] | None = None) -> dict[str, Any]:
        env = environ if environ is not None else dict(os.environ)
        api_key = (env.get("SAM_GOV_API_KEY") or "").strip()
        if not api_key:
            return {"source": "sam.gov", "promoted": [], "promoted_count": 0, "errors": ["SAM_GOV_API_KEY is not configured"], "configured": False}
        params = {
            "api_key": api_key,
            "q": keyword,
            "limit": max(1, min(int(limit), 100)),
        }
        promoted: list[dict[str, Any]] = []
        errors: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.get(SAM_OPPORTUNITIES_URL, params=params, headers={"User-Agent": "AION-Revenue-Scout/1.1"})
                response.raise_for_status()
                payload = response.json()
                for item in _sam_hits(payload):
                    row = _promote_contract(item, self.store)
                    if row:
                        promoted.append(row)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:240])
        return {"source": "sam.gov", "promoted": promoted, "promoted_count": len(promoted), "errors": errors, "configured": True}

    async def scan_all(self) -> dict[str, Any]:
        grants = await self.scan_grants()
        sam = await self.scan_sam()
        return {
            "grants": grants,
            "sam": sam,
            "promoted_count": int(grants["promoted_count"]) + int(sam["promoted_count"]),
            "outbound_enabled": False,
            "application_or_bid_authority": False,
        }
