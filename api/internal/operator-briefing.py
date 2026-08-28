"""Owner-only AION operator briefing and capability registry.

This endpoint reports only capabilities actually present in the AION runtime.
Unsupported external connections are shown as unavailable rather than inferred.
"""
from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from aion.moltbook.settings import load_moltbook_settings
from aion.phase2_services import get_services, reset_services_cache
from aion.runtime_status import build_runtime_status

app = FastAPI()
REVIEW_PREFIX = "moltbook_opportunity_review:"
POSITIVE_DISPOSITIONS = {"strong_lead", "possible_lead"}


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
    precision = positive / reviewed if reviewed else None
    return {
        "reviewed": reviewed,
        "positive": positive,
        "precision": precision,
        "target_precision": 0.70,
        "minimum_reviews": 5,
        "ready": reviewed >= 5 and precision is not None and precision >= 0.70,
    }


def _capabilities(runtime: dict[str, Any], settings, quality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "conversation",
            "label": "AION conversation",
            "read": True,
            "propose": True,
            "approve": False,
            "execute": bool(runtime.get("providers", {}).get("openai_configured") or runtime.get("providers", {}).get("vercel_ai_gateway_fallback_eligible")),
            "scope": "Reasoning and web-assisted answers; consequential external actions remain separately gated.",
        },
        {
            "id": "memory",
            "label": "Durable memory",
            "read": bool(runtime.get("storage", {}).get("configured")),
            "propose": False,
            "approve": True,
            "execute": bool(runtime.get("storage", {}).get("configured")),
            "scope": "Explicit remember / forget / replace operations and read-only owner inspection.",
        },
        {
            "id": "moltbook",
            "label": "Moltbook",
            "read": bool(settings.configured_for_live),
            "propose": bool(settings.configured_for_live),
            "approve": bool(settings.outbound_enabled and quality.get("ready")),
            "execute": bool(settings.controlled_outbound_ready),
            "scope": "Research and proposals; controlled execution is comments only. No DMs or autonomous writes.",
        },
        {
            "id": "terminal",
            "label": "Safe executor",
            "read": bool(runtime.get("operations", {}).get("terminal_executor_connected")),
            "propose": True,
            "approve": True,
            "execute": bool(runtime.get("operations", {}).get("terminal_executor_connected")),
            "scope": "Owner-gated fixed inspect/lint/build/all diagnostics in ephemeral Vercel Sandbox; no arbitrary shell.",
        },
        {
            "id": "paper_market",
            "label": "Paper market",
            "read": True,
            "propose": True,
            "approve": False,
            "execute": True,
            "scope": "Virtual BTC/ETH paper simulation only; no wallet, exchange, or live trading capability.",
        },
        {
            "id": "github_runtime",
            "label": "GitHub inside AION runtime",
            "read": False,
            "propose": False,
            "approve": False,
            "execute": False,
            "scope": "No GitHub connector is exposed to the deployed AION runtime yet. Repository work remains an owner/tooling workflow outside the app runtime.",
        },
        {
            "id": "notifications",
            "label": "External notifications",
            "read": False,
            "propose": False,
            "approve": False,
            "execute": False,
            "scope": "No email, SMS, call, or push delivery connector is currently exposed to the AION runtime.",
        },
    ]


@app.get("/api/internal/operator-briefing")
async def operator_briefing(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_owner(authorization)
    reset_services_cache()
    svc = get_services()
    runtime = build_runtime_status()
    settings = load_moltbook_settings()
    quality = _quality(svc)
    approvals = [req.redacted() for req in svc.gate.list_all()]
    pending = [item for item in approvals if item.get("decision") == "pending"]
    leads = svc.store.list_leads()
    audits = svc.store.list_audit(limit=12)

    actions: list[str] = []
    if not runtime.get("providers", {}).get("openai_configured"):
        actions.append("Direct OpenAI is not configured; AION may depend on Gateway fallback.")
    if quality["reviewed"] < quality["minimum_reviews"]:
        actions.append(f"Review at least {quality['minimum_reviews'] - quality['reviewed']} more qualified opportunities before controlled Moltbook approval can unlock.")
    elif not quality["ready"]:
        actions.append("Opportunity precision is below the 70% controlled-outbound quality threshold; continue labeling leads before activation.")
    if pending:
        actions.append(f"{len(pending)} Moltbook proposal(s) are awaiting owner review.")
    if not settings.outbound_enabled:
        actions.append("Moltbook outbound approval remains deployment-locked.")
    elif not settings.execute_enabled:
        actions.append("Moltbook execution remains separately deployment-locked.")
    if not runtime.get("operations", {}).get("terminal_executor_connected"):
        actions.append("Safe sandbox executor is not connected in this runtime.")

    return {
        "ok": True,
        "mode": "owner-operator-briefing",
        "runtime": runtime,
        "quality": quality,
        "counts": {
            "qualified_leads": len(leads),
            "pending_approvals": len(pending),
            "recent_audit_events": len(audits),
        },
        "capabilities": _capabilities(runtime, settings, quality),
        "actions_needed": actions,
        "recent_audit": audits,
        "principle": "Each capability advances independently through read → propose → approve → execute. A global autonomy switch is not used as a substitute for capability-specific permission.",
    }
