"""Owner Phase 2 service facade used by API and dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from aion.commercial_execution import build_execution_plans
from aion.fulfillment import fulfill_paid_orders
from aion.moltbook.approval import Phase2ApprovalGate
from aion.moltbook.client import create_client
from aion.moltbook.controlled_autonomy import ControlledAutonomyEngine
from aion.moltbook.drafts import CampaignDraftService
from aion.moltbook.leads import LeadDiscoveryService, SEARCH_CATEGORIES
from aion.moltbook.security import KillSwitch
from aion.durable.db import storage_status
from aion.durable.paths import resolve_durable_paths
from aion.durable.scheduler_store import SchedulerStore
from aion.external_scouts import ExternalRevenueScout, default_sources
from aion.federal_scouts import FederalOpportunityScout
from aion.moltbook.store import Phase2Store
from aion.opportunity_qualification import qualify_ranked
from aion.opportunity_store import OpportunityStore
from aion.paper_trading import PaperConfig, PaperTradingEngine
from aion.paper_trading.cached_prices import CachedPriceProvider
from aion.pursuit_packets import build_top_packets
from aion.revenue_pipeline import promote_leads


@dataclass(slots=True)
class Phase2Services:
    store: Phase2Store
    opportunity_store: OpportunityStore
    kill_switch: KillSwitch
    gate: Phase2ApprovalGate
    drafts: CampaignDraftService
    paper: PaperTradingEngine
    autonomy: ControlledAutonomyEngine
    scheduler: SchedulerStore

    def leads(self) -> LeadDiscoveryService:
        return LeadDiscoveryService(self.store, create_client())

    def external_scout(self) -> ExternalRevenueScout:
        return ExternalRevenueScout(self.opportunity_store)

    def federal_scout(self) -> FederalOpportunityScout:
        return FederalOpportunityScout(self.opportunity_store)

    async def scan_external_opportunities(self) -> dict[str, Any]:
        return await self.external_scout().scan(default_sources())

    async def scan_federal_opportunities(self) -> dict[str, Any]:
        return await self.federal_scout().scan_all()

    def promote_current_leads(self) -> list[dict[str, Any]]:
        return promote_leads(self.store.list_leads(), self.opportunity_store)


@lru_cache(maxsize=1)
def get_services() -> Phase2Services:
    paths = resolve_durable_paths()
    db = os.getenv("AION_PHASE2_DB") or str(paths.phase2_db)
    store = Phase2Store(db)
    opportunity_store = OpportunityStore(db)
    kill = KillSwitch.from_env()
    store.set_risk("kill_switch", kill.snapshot())
    gate = Phase2ApprovalGate(store, kill_switch=kill)
    drafts = CampaignDraftService(store, gate)
    paper_db = os.getenv("AION_PAPER_DB") or str(paths.paper_db)
    price_mode = os.getenv("AION_PAPER_PRICE_MODE", "live_public")
    paper = PaperTradingEngine(
        PaperConfig(db_path=paper_db),
        prices=CachedPriceProvider(mode=price_mode, ttl_seconds=60.0),
    )
    autonomy = ControlledAutonomyEngine.create(store, kill_switch=kill)
    scheduler = SchedulerStore(store)
    return Phase2Services(
        store=store,
        opportunity_store=opportunity_store,
        kill_switch=kill,
        gate=gate,
        drafts=drafts,
        paper=paper,
        autonomy=autonomy,
        scheduler=scheduler,
    )


def reset_services_cache() -> None:
    get_services.cache_clear()


def dashboard_snapshot() -> dict[str, Any]:
    svc = get_services()
    pending = [r.redacted() for r in svc.gate.list_pending()]
    all_approvals = [r.redacted() for r in svc.gate.list_all()]
    rejected = [r for r in all_approvals if r["decision"] == "rejected"]
    approved = [r for r in all_approvals if r["decision"] in {"approved", "executed"}]
    paper = svc.paper.performance_report()
    autonomy_status = svc.autonomy.status()
    qualified_leads = svc.store.list_leads()
    promoted = promote_leads(qualified_leads, svc.opportunity_store)
    ranked_opportunities = svc.opportunity_store.top(limit=25)
    pursuit_ranked = qualify_ranked(ranked_opportunities)
    pursuit_packets = build_top_packets(pursuit_ranked, limit=5)
    execution_plans = build_execution_plans(ranked_opportunities, limit=10)
    try:
        payment_orders = svc.opportunity_store.list_payment_orders(limit=50)
    except Exception:  # noqa: BLE001
        payment_orders = []
    payment_pending = [o for o in payment_orders if o.get("status") == "pending_owner_approval"]
    payment_paid = [o for o in payment_orders if o.get("status") == "paid"]
    payment_fulfilled = [o for o in payment_orders if o.get("status") == "fulfilled"]
    source_counts: dict[str, int] = {}
    for row in ranked_opportunities:
        scout = str(row.get("scout") or "unknown")
        source_counts[scout] = source_counts.get(scout, 0) + 1
    pursuit_counts: dict[str, int] = {}
    for row in pursuit_ranked:
        recommendation = str((row.get("qualification") or {}).get("recommendation") or "unknown")
        pursuit_counts[recommendation] = pursuit_counts.get(recommendation, 0) + 1
    return {
        "phase": "phase2-controlled-growth",
        "storage": storage_status().as_dict(),
        "kill_switch": svc.kill_switch.snapshot(),
        "drafts_awaiting_approval": svc.drafts.list_drafts(),
        "approvals_pending": pending,
        "approvals_approved": approved,
        "approvals_rejected": rejected,
        "qualified_leads": qualified_leads,
        "opportunities_promoted": len(promoted),
        "ranked_opportunities": ranked_opportunities,
        "pursuit_ranked_opportunities": pursuit_ranked,
        "pursuit_recommendation_counts": pursuit_counts,
        "pursuit_packets": pursuit_packets,
        "top_pursuit_packet": pursuit_packets[0] if pursuit_packets else None,
        "commercial_execution_plans": execution_plans,
        "commercial_execution_ready_count": sum(1 for plan in execution_plans if plan.get("executable")),
        "payment_orders": {
            "all": payment_orders,
            "pending_approval": payment_pending,
            "paid_awaiting_fulfillment": payment_paid,
            "fulfilled": payment_fulfilled,
            "total_paid_amount_cents": sum(int(o.get("amount_cents") or 0) for o in payment_paid),
            "total_fulfilled_amount_cents": sum(int(o.get("amount_cents") or 0) for o in payment_fulfilled),
        },
        "opportunity_source_counts": source_counts,
        "highest_probability_legitimate_action": pursuit_ranked[0] if pursuit_ranked else None,
        "realized_value_total": sum(float(row.get("realized_value") or 0) for row in ranked_opportunities),
        "yalitek_conversions": [lead for lead in qualified_leads if lead.get("conversion_outcome") not in {"uncontacted", None, ""}],
        "attributed_revenue_total": sum(float(lead.get("revenue_attributed") or 0) for lead in qualified_leads),
        "paper_trading": paper,
        "controlled_autonomy": autonomy_status,
        "search_categories": [c["service"] for c in SEARCH_CATEGORIES],
        "external_scout_sources": [
            {"name": source.name, "host": source.url.split("/")[2], "scout": source.scout}
            for source in default_sources()
        ],
        "federal_scout_sources": [
            {"name": "grants.gov", "mode": "public_no_auth"},
            {"name": "sam.gov", "mode": "api_key_if_configured", "configured": bool((os.getenv("SAM_GOV_API_KEY") or "").strip())},
        ],
        "qualification_configuration": {
            "sam_registration_verified": (os.getenv("AION_SAM_REGISTERED") or "").strip().lower() in {"1", "true", "yes", "on"},
            "small_business_verified": (os.getenv("AION_SMALL_BUSINESS_VERIFIED") or "").strip().lower() in {"1", "true", "yes", "on"},
            "grant_eligibility_verified": (os.getenv("AION_GRANT_ELIGIBILITY_VERIFIED") or "").strip().lower() in {"1", "true", "yes", "on"},
            "principle": "unknown eligibility remains unknown until owner-verified",
        },
        "audit_history": svc.store.list_audit(limit=50),
        "risk_status": {
            "kill_switch": svc.kill_switch.snapshot(),
            "outbound_execute_enabled": False,
            "controlled_autonomy_mode": autonomy_status["policy"]["mode"],
            "controlled_autonomy_dry_run": autonomy_status["dry_run"],
            "live_writes_enabled": autonomy_status["live_writes_enabled"],
            "notes": [
                "Drafts are not published automatically.",
                "Controlled autonomy defaults to inactive + dry_run.",
                "Opportunity discovery never grants transaction authority.",
                "External and federal scout content is untrusted and read-only.",
                "Pursuit packets prepare materials but cannot send, submit, bid, apply, register, or transact.",
                "Controlled commercial execution currently supports only eligible public Moltbook comments using exact-content single-use owner approval.",
                "Generic external outreach, grant submission, and federal bid submission remain disabled.",
                "Grant applications and contract bids always require owner authorization.",
                "Eligibility is never inferred from marketing language or public opportunity text.",
                "Revenue estimates remain zero unless an explicit public amount is found.",
                "Paper trading uses virtual funds only.",
                "No exchange trading keys accepted.",
                "Final owner activation required before any autonomous write.",
            ],
        },
    }
