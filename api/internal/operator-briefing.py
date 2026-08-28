"""Owner-only AION operator briefing grounded in durable runtime state."""
from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from aion.capabilities import capability_registry
from aion.phase2_services import get_services, reset_services_cache
from aion.runtime_status import build_runtime_status

app = FastAPI()
REVIEW_PREFIX = "moltbook_opportunity_review:"
POSITIVE_DISPOSITIONS = {"strong_lead", "possible_lead"}
MIN_REVIEWS = 5
TARGET_PRECISION = 0.70


def _require_owner(authorization: str | None) -> None:
    token = (os.getenv("AION_OWNER_TOKEN") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _quality(svc) -> dict[str, Any]:
    rows = svc.store.list_risk_prefix(REVIEW_PREFIX)
    dispositions = [str((row.get("value") or {}).get("disposition") or "") for row in rows]
    reviewed = len(dispositions)
    positive = sum(1 for value in dispositions if value in POSITIVE_DISPOSITIONS)
    precision = (positive / reviewed) if reviewed else None
    return {
        "reviewed": reviewed,
        "positive": positive,
        "precision": precision,
        "target_precision": TARGET_PRECISION,
        "minimum_reviews": MIN_REVIEWS,
        "ready": reviewed >= MIN_REVIEWS and precision is not None and precision >= TARGET_PRECISION,
    }


@app.get("/api/internal/operator-briefing")
async def operator_briefing(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    runtime = build_runtime_status()
    registry = capability_registry()
    quality = _quality(svc)
    approvals = [req.redacted() for req in svc.gate.list_all()]
    pending = [item for item in approvals if item.get("decision") == "pending"]
    leads = svc.store.list_leads()
    audits = svc.store.list_audit(limit=12)

    actions: list[str] = []
    if not runtime.get("providers", {}).get("openai_configured"):
        actions.append("Direct OpenAI is not configured; AION may depend on Gateway fallback.")
    if quality["reviewed"] < MIN_REVIEWS:
        actions.append(f"Review {MIN_REVIEWS - quality['reviewed']} more qualified opportunity(ies) before the Moltbook approval quality gate can unlock.")
    elif not quality["ready"]:
        actions.append("Opportunity precision is below the 70% controlled-outbound threshold; continue reviewing before activation.")
    if pending:
        actions.append(f"{len(pending)} Moltbook proposal(s) are awaiting owner review.")
    if not runtime.get("moltbook", {}).get("outbound_enabled"):
        actions.append("Moltbook outbound approval remains deployment-locked.")
    elif not runtime.get("moltbook", {}).get("execute_enabled"):
        actions.append("Moltbook execution remains separately deployment-locked.")
    if not runtime.get("operations", {}).get("terminal_executor_connected"):
        actions.append("Safe Vercel Sandbox executor is not connected in this runtime.")

    return {
        "ok": True,
        "mode": "owner-operator-briefing",
        "quality": quality,
        "counts": {
            "qualified_leads": len(leads),
            "pending_approvals": len(pending),
            "recent_audit_events": len(audits),
        },
        "capabilities": registry["capabilities"],
        "actions_needed": actions,
        "recent_audit": audits,
        "principle": "Each capability advances independently through read → propose → approve → execute. A global unrestricted autonomy switch is not available.",
    }
