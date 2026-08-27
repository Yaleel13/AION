#!/usr/bin/env python3
"""14-day experiment operations cycle (remaining phases).

Runs non-spammy Phase 2 + controlled-autonomy ops that are allowed now:

1. Seed draft campaign if empty (no publish)
2. Paper-trading tick (virtual funds only)
3. Lead discovery + customized response drafts
4. Daily owner report
5. Flush queued outbound only when quotas allow

Never raises quotas, sends DMs, prices work, or places live trades.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)


def _customize_lead_response(lead: dict) -> str:
    service = str(lead.get("relevant_service") or "technical help")
    problem = str(lead.get("stated_problem") or "the issue you described")
    return (
        f"Public reply draft (owner approval still required before any off-platform move):\n\n"
        f"I noticed you described a need around “{problem[:140]}”. "
        f"One practical first step is a short, non-sensitive diagnostic: symptoms, when it started, "
        f"and what you already tried. YaliTek Online’s relevant offering here is {service} — "
        f"reviewed delivery, not unattended automation.\n\n"
        f"If a public reply is appropriate, I can share a lightweight checklist first "
        f"(useful even if you never hire anyone). I will not ask for credentials, files, "
        f"or access in public, and I will not quote pricing here."
    )


async def run_cycle(*, flush_queue: bool) -> dict:
    from aion.moltbook.autonomy_policy import qualify_outbound_content
    from aion.moltbook.client import create_client
    from aion.phase2_services import dashboard_snapshot, get_services, reset_services_cache

    reset_services_cache()
    svc = get_services()
    result: dict = {
        "phase": "experiment-ops",
        "kill_switch": svc.kill_switch.snapshot(),
        "published": False,
    }

    if svc.kill_switch.engaged:
        result["stopped"] = "kill_switch_engaged"
        return result

    # 1) Draft campaign seed
    drafts = svc.drafts.list_drafts()
    if not drafts:
        created = svc.drafts.seed_fourteen_day_campaign()
        result["drafts_seeded"] = len(created)
    else:
        result["drafts_existing"] = len(drafts)

    # 2) Paper trading tick (virtual only)
    try:
        paper = svc.paper.run_starter_strategy_once()
        report = svc.paper.performance_report()
        result["paper"] = {
            "equity": paper.get("mark", {}).get("equity"),
            "return_pct": paper.get("mark", {}).get("return_pct"),
            "price_source": (paper.get("mark", {}).get("positions") or {}).get(
                "price_source"
            ),
            "ready_for_live_proposal": report.get("ready_for_live_proposal"),
            "disclaimer": "Paper only — no wallets/exchanges/live orders",
        }
    except Exception as exc:  # noqa: BLE001
        # Public price APIs can 429; keep cycle alive without live trading.
        latest = (svc.paper.performance_report().get("latest") or {})
        result["paper"] = {
            "equity": latest.get("equity"),
            "return_pct": latest.get("return_pct"),
            "price_source": (latest.get("positions") or {}).get("price_source"),
            "ready_for_live_proposal": False,
            "tick_error": str(exc)[:200],
            "disclaimer": "Paper only — tick skipped due to price feed error",
        }

    # 3) Lead discovery + customized drafts
    leads = await svc.leads().scan_feed(limit=40)
    prepared = []
    for lead in leads:
        custom = _customize_lead_response(lead)
        lead["suggested_response"] = custom
        svc.store.upsert_lead(lead)
        item = {
            "lead_id": lead["lead_id"],
            "service": lead["relevant_service"],
            "confidence": lead["confidence_score"],
            "source_url": lead["source_url"],
            "suggested_response": custom,
            "approval_status": lead["approval_status"],
        }
        prepared.append(item)
        if float(lead.get("confidence_score") or 0) >= 0.7:
            svc.autonomy.alert_owner_lead(lead)
    result["leads_prepared"] = prepared

    # 4) Daily report
    report = svc.autonomy.build_daily_report()
    result["daily_report"] = {
        "date": report["date"],
        "actions": len(report.get("posts_comments_follows") or []),
        "blocks": len(report.get("actions_blocked") or []),
        "leads": len(report.get("leads_discovered") or []),
        "recommended_owner_decisions": report.get("recommended_owner_decisions"),
    }

    # 5) Optional queue flush (only if quota allows)
    queued = svc.store.get_risk("queued_outbound") or {}
    result["queued_outbound"] = queued
    result["counters"] = svc.autonomy.status()["counters"]
    if flush_queue and queued.get("type") == "queued_comment":
        comment_count = int(result["counters"]["comment"]["count"])
        comment_limit = int(svc.autonomy.policy.limits.max_comments_per_24h)
        if comment_count < comment_limit and not svc.autonomy.dry_run:
            content = str(queued.get("content") or "")
            post_id = str(queued.get("post_id") or "")
            verdict = qualify_outbound_content(
                action="comment",
                text=content,
                destination=f"post:{post_id}",
            )
            if verdict.allowed and post_id and content:
                published = await svc.autonomy.execute_comment(
                    post_id=post_id,
                    content=content,
                    idempotency_key=f"queued-comment-{post_id[:8]}",
                )
                result["queue_flush"] = published
                result["published"] = bool(published.get("published"))
                if published.get("published"):
                    svc.store.set_risk("queued_outbound", {"status": "published", "result": published})
            else:
                result["queue_flush"] = {"skipped": "policy_blocked", "reasons": verdict.reasons}
        else:
            result["queue_flush"] = {
                "skipped": "comment_quota_or_dry_run",
                "comment_count": comment_count,
                "limit": comment_limit,
                "dry_run": svc.autonomy.dry_run,
            }

    # Next draft ready for when post quota frees (not published)
    awaiting = [
        d
        for d in svc.drafts.list_drafts()
        if not d.get("approval_request_id")
    ]
    if awaiting:
        nxt = sorted(awaiting, key=lambda d: int(d.get("day_index") or 0))[0]
        result["next_post_draft"] = {
            "draft_id": nxt.get("draft_id"),
            "day_index": nxt.get("day_index"),
            "title": nxt.get("title"),
            "submolt": nxt.get("submolt"),
            "theme": nxt.get("theme"),
            "approval_request_id": nxt.get("approval_request_id"),
            "note": "Held until create_post quota frees; still subject to policy + verification",
        }

    result["dashboard"] = {
        "phase": dashboard_snapshot().get("phase"),
        "live_writes_enabled": svc.autonomy.status().get("live_writes_enabled"),
    }
    # silence unused import warning path for create_client in dry environments
    _ = create_client
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--flush-queue",
        action="store_true",
        help="Attempt to publish queued outbound if quotas allow",
    )
    parser.add_argument(
        "--out",
        default="/tmp/aion_experiment_ops_cycle.json",
        help="Write JSON summary to this path",
    )
    args = parser.parse_args()

    import asyncio

    payload = asyncio.run(run_cycle(flush_queue=args.flush_queue))
    Path(args.out).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
