#!/usr/bin/env python3
"""14-day experiment operations cycle (remaining phases).

Runs non-spammy Phase 2 + controlled-autonomy ops that are allowed now:

1. Seed draft campaign if empty (no publish)
2. Paper-trading tick (virtual funds only)
3. Lead discovery + product matching + customized response drafts
4. Convert at most one explicit high-confidence public buyer lead when policy/quota allow
5. Daily owner report
6. Flush queued outbound only when quotas allow
7. Publish next campaign draft only when post quota allows

Never raises quotas, sends unsolicited DMs, invents pricing, or places live trades.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from aion.moltbook.experiment_ops import (
    customize_lead_response,
    mark_backlog_status,
    refresh_queue_timing,
    select_conversion_candidate,
    select_next_backlog_comment,
    select_next_campaign_draft,
)
from aion.revenue.product_catalog import commercial_inventory_snapshot, match_product_for_lead

load_dotenv(ROOT / ".env", override=True)


async def run_cycle(
    *,
    flush_queue: bool,
    publish_next_draft: bool,
) -> dict:
    from aion.moltbook.autonomy_policy import qualify_outbound_content
    from aion.moltbook.client import create_client
    from aion.moltbook.controlled_autonomy import AutonomyBlockedError
    from aion.phase2_services import dashboard_snapshot, get_services, reset_services_cache

    reset_services_cache()
    svc = get_services()
    result: dict = {
        "phase": "experiment-ops",
        "kill_switch": svc.kill_switch.snapshot(),
        "published": False,
        "commercial_inventory": {
            "total_inventory_count": commercial_inventory_snapshot()["total_inventory_count"],
            "sale_ready_count": commercial_inventory_snapshot()["sale_ready_count"],
        },
    }

    if svc.kill_switch.engaged:
        result["stopped"] = "kill_switch_engaged"
        return result

    # 1) Draft campaign seed
    drafts = svc.drafts.list_drafts()
    if not drafts:
        created = svc.drafts.seed_fourteen_day_campaign()
        result["drafts_seeded"] = len(created)
        drafts = svc.drafts.list_drafts()
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
        latest = (svc.paper.performance_report().get("latest") or {})
        result["paper"] = {
            "equity": latest.get("equity"),
            "return_pct": latest.get("return_pct"),
            "price_source": (latest.get("positions") or {}).get("price_source"),
            "ready_for_live_proposal": False,
            "tick_error": str(exc)[:200],
            "disclaimer": "Paper only — tick skipped due to price feed error",
        }

    # 3) Lead discovery + product matching + customized drafts
    leads = await svc.leads().scan_feed(limit=40)
    prepared = []
    for lead in leads:
        custom = customize_lead_response(lead)
        lead["suggested_response"] = custom
        svc.store.upsert_lead(lead)
        product = match_product_for_lead(lead)
        item = {
            "lead_id": lead["lead_id"],
            "service": lead["relevant_service"],
            "confidence": lead["confidence_score"],
            "source_url": lead["source_url"],
            "matched_venture": product.venture,
            "matched_product": product.name,
            "matched_product_key": product.product_key,
            "sale_status": product.sale_status,
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

    # Establish current comment capacity once, then let buyer-intent conversion have
    # first access to a slot before lower-priority generic queue/backlog activity.
    result["counters"] = svc.autonomy.status()["counters"]
    comment_count = int(result["counters"]["comment"]["count"])
    comment_limit = int(svc.autonomy.policy.effective_limits().max_comments_per_24h)
    comment_slots = max(0, comment_limit - comment_count)

    # 5) Tight buyer-intent -> controlled public conversion handoff.
    # At most one public reply per cycle. It must be explicit buyer intent, >=0.70
    # confidence, a real Moltbook post, policy-allowed, quota/pacing-allowed, and
    # idempotent by stable source post ID. No DM is sent.
    conversion = select_conversion_candidate(leads)
    if conversion:
        product = match_product_for_lead(conversion)
        result["conversion_candidate"] = {
            "lead_id": conversion.get("lead_id"),
            "post_id": conversion.get("source_post_id"),
            "confidence": conversion.get("confidence_score"),
            "venture": product.venture,
            "product": product.name,
            "product_key": product.product_key,
            "sale_status": product.sale_status,
            "checkout_verified": bool(product.checkout_url),
        }
        if flush_queue and comment_slots > 0 and not svc.autonomy.dry_run:
            post_id = str(conversion.get("source_post_id") or "")
            content = str(conversion.get("suggested_response") or "")
            verdict = qualify_outbound_content(
                action="comment",
                text=content,
                destination=f"post:{post_id}",
                inbound_context=str(conversion.get("raw_excerpt") or conversion.get("stated_problem") or ""),
            )
            if verdict.allowed and post_id and content:
                try:
                    published = await svc.autonomy.execute_comment(
                        post_id=post_id,
                        content=content,
                        idempotency_key=f"qualified-buyer-{post_id}",
                        target_account=str(conversion.get("requester_identity") or "") or None,
                        solicited=False,
                    )
                except AutonomyBlockedError as exc:
                    result["conversion_handoff"] = {
                        "skipped": "policy_pacing_quota_or_duplicate",
                        "reason": str(exc),
                        "post_id": post_id,
                    }
                except Exception as exc:  # noqa: BLE001
                    result["conversion_handoff"] = {
                        "skipped": "execution_error",
                        "reason": str(exc)[:300],
                        "post_id": post_id,
                    }
                else:
                    result["conversion_handoff"] = {
                        "result": published,
                        "post_id": post_id,
                        "product_key": product.product_key,
                    }
                    result["published"] = result["published"] or bool(published.get("published"))
                    if published.get("published"):
                        comment_slots = max(0, comment_slots - 1)
                        result["counters"] = svc.autonomy.status()["counters"]
            else:
                result["conversion_handoff"] = {
                    "skipped": "content_policy_blocked",
                    "reasons": verdict.reasons,
                    "post_id": post_id,
                }
        else:
            result["conversion_handoff"] = {
                "skipped": "not_executable_now",
                "flush_queue": flush_queue,
                "comment_slots": comment_slots,
                "dry_run": svc.autonomy.dry_run,
            }
    else:
        result["conversion_candidate"] = None
        result["conversion_handoff"] = {"skipped": "no_explicit_high_confidence_buyer"}

    # 6) Optional legacy queue flush (only if quota allows)
    queued = refresh_queue_timing(svc.store.get_risk("queued_outbound") or {})
    if queued.get("type") == "queued_comment":
        svc.store.set_risk("queued_outbound", queued)
    result["queued_outbound"] = queued

    if flush_queue and queued.get("type") == "queued_comment":
        if comment_slots > 0 and not svc.autonomy.dry_run:
            content = str(queued.get("content") or "")
            post_id = str(queued.get("post_id") or "")
            verdict = qualify_outbound_content(
                action="comment",
                text=content,
                destination=f"post:{post_id}",
            )
            if verdict.allowed and post_id and content:
                try:
                    published = await svc.autonomy.execute_comment(
                        post_id=post_id,
                        content=content,
                        idempotency_key=f"queued-comment-{post_id[:8]}",
                        target_account=str(queued.get("in_reply_to_author") or "")
                        or None,
                        solicited=True,
                    )
                except AutonomyBlockedError as exc:
                    result["queue_flush"] = {
                        "skipped": "pacing_or_quota",
                        "reason": str(exc),
                    }
                else:
                    result["queue_flush"] = published
                    result["published"] = result["published"] or bool(published.get("published"))
                    if published.get("published"):
                        svc.store.set_risk(
                            "queued_outbound",
                            {"status": "published", "result": published},
                        )
                        comment_slots = max(0, comment_slots - 1)
                        result["counters"] = svc.autonomy.status()["counters"]
            else:
                result["queue_flush"] = {
                    "skipped": "policy_blocked",
                    "reasons": verdict.reasons,
                }
        else:
            result["queue_flush"] = {
                "skipped": "comment_quota_or_dry_run",
                "comment_count": int(result["counters"]["comment"]["count"]),
                "limit": comment_limit,
                "dry_run": svc.autonomy.dry_run,
                "first_slot_frees_at": (queued.get("publish_when") or {}).get(
                    "first_slot_frees_at"
                ),
            }

    # 6b) Flush prioritized comment backlog when slots remain
    backlog_state = svc.store.get_risk("comment_backlog") or {}
    backlog = list(backlog_state.get("backlog") or [])
    result["comment_backlog_ready"] = sum(
        1
        for item in backlog
        if item.get("status") == "ready" and item.get("policy_allowed") and item.get("content")
    )
    if flush_queue and comment_slots > 0 and not svc.autonomy.dry_run:
        nxt_comment = select_next_backlog_comment(backlog)
        if nxt_comment:
            content = str(nxt_comment.get("content") or "")
            post_id = str(nxt_comment.get("post_id") or "")
            verdict = qualify_outbound_content(
                action="comment",
                text=content,
                destination=f"post:{post_id}",
            )
            if verdict.allowed and post_id and content:
                try:
                    published = await svc.autonomy.execute_comment(
                        post_id=post_id,
                        content=content,
                        idempotency_key=(
                            f"backlog-p{nxt_comment.get('priority')}-{post_id[:8]}"
                        ),
                        target_account=str(nxt_comment.get("author") or "") or None,
                        solicited=bool(
                            nxt_comment.get("reason")
                            in {"reply_on_our_intro", "direct_mention"}
                        ),
                    )
                except AutonomyBlockedError as exc:
                    result["backlog_flush"] = {
                        "skipped": "pacing_or_quota",
                        "reason": str(exc),
                        "priority": nxt_comment.get("priority"),
                    }
                else:
                    result["backlog_flush"] = {
                        "priority": nxt_comment.get("priority"),
                        "author": nxt_comment.get("author"),
                        "post_id": post_id,
                        "result": published,
                    }
                    result["published"] = result["published"] or bool(
                        published.get("published")
                    )
                    if published.get("published"):
                        backlog = mark_backlog_status(
                            backlog,
                            post_id=post_id,
                            priority=int(nxt_comment.get("priority") or 0),
                            status="published",
                        )
                        backlog_state = {
                            **backlog_state,
                            "type": "comment_backlog",
                            "backlog": backlog,
                            "primary_queue": svc.store.get_risk("queued_outbound") or {},
                        }
                        svc.store.set_risk("comment_backlog", backlog_state)
                        result["counters"] = svc.autonomy.status()["counters"]
            else:
                result["backlog_flush"] = {
                    "skipped": "policy_blocked",
                    "reasons": verdict.reasons,
                    "priority": nxt_comment.get("priority"),
                }
        else:
            result["backlog_flush"] = {"skipped": "no_ready_backlog"}
    elif flush_queue:
        result["backlog_flush"] = {
            "skipped": "comment_quota_or_dry_run",
            "comment_slots": comment_slots,
            "ready": result["comment_backlog_ready"],
        }

    # 7) Optional next-draft publish (only if post quota allows)
    nxt = select_next_campaign_draft(drafts)
    if nxt:
        result["next_post_draft"] = {
            "draft_id": nxt.get("draft_id"),
            "day_index": nxt.get("day_index"),
            "title": nxt.get("title"),
            "submolt": nxt.get("submolt"),
            "theme": nxt.get("theme"),
            "approval_request_id": nxt.get("approval_request_id"),
            "note": (
                "Held until create_post quota frees; still subject to policy + verification"
            ),
        }
    if publish_next_draft and nxt:
        post_count = int(result["counters"]["create_post"]["count"])
        post_limit = int(svc.autonomy.policy.effective_limits().max_posts_per_24h)
        if post_count < post_limit and not svc.autonomy.dry_run:
            title = str(nxt.get("title") or "")
            body = str(nxt.get("body") or "")
            submolt = str(nxt.get("submolt") or "general")
            text = f"{title}\n{body}"
            verdict = qualify_outbound_content(
                action="create_post",
                text=text,
                destination=f"submolt:{submolt}",
            )
            if verdict.allowed and title and body:
                try:
                    published = await svc.autonomy.execute_post(
                        submolt=submolt,
                        title=title,
                        content=body,
                        idempotency_key=f"campaign-day-{nxt.get('day_index')}-{str(nxt.get('draft_id'))[:8]}",
                    )
                except Exception as exc:  # noqa: BLE001 — pacing, verify, or platform
                    result["draft_publish"] = {
                        "skipped": "execute_error",
                        "reason": str(exc)[:300],
                    }
                else:
                    result["draft_publish"] = published
                    result["published"] = result["published"] or bool(
                        published.get("published")
                    )
                    marker = (
                        published.get("post_id")
                        or published.get("url")
                        or ("dry" if published.get("dry_run") else "attempted")
                    )
                    if published.get("published") or published.get("post_id"):
                        svc.store.update_draft_approval(
                            str(nxt["draft_id"]), f"autonomy:{marker}"
                        )
                        result["next_post_draft"]["approval_request_id"] = (
                            f"autonomy:{marker}"
                        )
                        result["next_post_draft"]["note"] = (
                            "Published under controlled autonomy"
                        )
            else:
                result["draft_publish"] = {
                    "skipped": "policy_blocked",
                    "reasons": verdict.reasons,
                }
        else:
            result["draft_publish"] = {
                "skipped": "post_quota_or_dry_run",
                "post_count": post_count,
                "limit": post_limit,
                "dry_run": svc.autonomy.dry_run,
            }

    result["dashboard"] = {
        "phase": dashboard_snapshot().get("phase"),
        "live_writes_enabled": svc.autonomy.status().get("live_writes_enabled"),
    }
    _ = create_client
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--flush-queue",
        action="store_true",
        help="Attempt qualified buyer conversion then queued outbound if quotas allow",
    )
    parser.add_argument(
        "--publish-next-draft",
        action="store_true",
        help="Attempt to publish the next campaign draft if post quota allows",
    )
    parser.add_argument(
        "--out",
        default="/tmp/aion_experiment_ops_cycle.json",
        help="Write JSON summary to this path",
    )
    args = parser.parse_args()

    import asyncio

    payload = asyncio.run(
        run_cycle(
            flush_queue=args.flush_queue,
            publish_next_draft=args.publish_next_draft,
        )
    )
    Path(args.out).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
