"""Owner Phase 2 service facade used by API and dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from aion.moltbook.approval import Phase2ApprovalGate
from aion.moltbook.client import create_client
from aion.moltbook.drafts import CampaignDraftService
from aion.moltbook.leads import LeadDiscoveryService, SEARCH_CATEGORIES
from aion.moltbook.security import KillSwitch
from aion.moltbook.store import DEFAULT_DB_PATH, Phase2Store
from aion.paper_trading import PaperConfig, PaperTradingEngine


@dataclass(slots=True)
class Phase2Services:
    store: Phase2Store
    kill_switch: KillSwitch
    gate: Phase2ApprovalGate
    drafts: CampaignDraftService
    paper: PaperTradingEngine

    def leads(self) -> LeadDiscoveryService:
        return LeadDiscoveryService(self.store, create_client())


@lru_cache(maxsize=1)
def get_services() -> Phase2Services:
    db = os.getenv("AION_PHASE2_DB", DEFAULT_DB_PATH)
    store = Phase2Store(db)
    kill = KillSwitch.from_env()
    store.set_risk("kill_switch", kill.snapshot())
    gate = Phase2ApprovalGate(store, kill_switch=kill)
    drafts = CampaignDraftService(store, gate)
    paper = PaperTradingEngine(
        PaperConfig(db_path=os.getenv("AION_PAPER_DB", "/tmp/aion_paper_trading.db"))
    )
    return Phase2Services(
        store=store, kill_switch=kill, gate=gate, drafts=drafts, paper=paper
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
    return {
        "phase": "phase2-controlled-growth",
        "kill_switch": svc.kill_switch.snapshot(),
        "drafts_awaiting_approval": svc.drafts.list_drafts(),
        "approvals_pending": pending,
        "approvals_approved": approved,
        "approvals_rejected": rejected,
        "qualified_leads": svc.store.list_leads(),
        "yalitek_conversions": [
            lead
            for lead in svc.store.list_leads()
            if lead.get("conversion_outcome") not in {"uncontacted", None, ""}
        ],
        "attributed_revenue_total": sum(
            float(lead.get("revenue_attributed") or 0) for lead in svc.store.list_leads()
        ),
        "paper_trading": paper,
        "search_categories": [c["service"] for c in SEARCH_CATEGORIES],
        "audit_history": svc.store.list_audit(limit=50),
        "risk_status": {
            "kill_switch": svc.kill_switch.snapshot(),
            "outbound_execute_enabled": False,
            "notes": [
                "Drafts are not published automatically.",
                "Paper trading uses virtual funds only.",
                "No exchange trading keys accepted.",
            ],
        },
    }
