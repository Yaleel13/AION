"""Owner Phase 2 service facade used by API and dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from aion.moltbook.approval import Phase2ApprovalGate
from aion.moltbook.client import create_client
from aion.moltbook.controlled_autonomy import ControlledAutonomyEngine
from aion.moltbook.drafts import CampaignDraftService
from aion.moltbook.leads import LeadDiscoveryService, SEARCH_CATEGORIES
from aion.moltbook.security import KillSwitch
from aion.durable.db import storage_status
from aion.durable.paths import resolve_durable_paths
from aion.durable.scheduler_store import SchedulerStore
from aion.moltbook.store import Phase2Store
from aion.opportunity_store import OpportunityStore
from aion.paper_trading import PaperConfig, PaperTradingEngine
from aion.paper_trading.cached_prices import CachedPriceProvider
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
        "highest_probability_legitimate_action": ranked_opportunities[0] if ranked_opportunities else None,
        "realized_value_total": sum(float(row.get("realized_value") or 0) for row in ranked_opportunities),
        "yalitek_conversions": [lead for lead in qualified_leads if lead.get("conversion_outcome") not in {"uncontacted", None, ""}],
        "attributed_revenue_total": sum(float(lead.get("revenue_attributed") or 0) for lead in qualified_leads),
        "paper_trading": paper,
        "controlled_autonomy": autonomy_status,
        "search_categories": [c["service"] for c in SEARCH_CATEGORIES],
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
                "Revenue estimates remain zero unless an explicit public amount is found.",
                "Paper trading uses virtual funds only.",
                "No exchange trading keys accepted.",
                "Final owner activation required before any autonomous write.",
            ],
        },
    }
