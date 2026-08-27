"""Controlled Moltbook outbound executor for the 14-day experiment.

Default: inactive. Set MOLTBOOK_CONTROLLED_AUTONOMY=true only after final owner
activation approval. Even when active, every outbound payload is scanned,
quota-checked, hashed, idempotent, and audited before/after execution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from aion.moltbook.approval import OutboundAction
from aion.moltbook.autonomy_policy import (
    CONTENT_GENERATION_RULES,
    AutonomyMode,
    AutonomyPolicy,
    qualify_outbound_content,
    scan_secrets_and_pii,
)
from aion.moltbook.autonomy_store import AutonomyStore
from aion.moltbook.client import MoltbookClient, create_client
from aion.moltbook.errors import MoltbookError, MoltbookOutboundDisabledError
from aion.moltbook.redact import redact_text, redact_value
from aion.moltbook.security import (
    KillSwitch,
    content_hash,
    detect_prompt_injection,
    utc_now,
    utc_now_iso,
)
from aion.moltbook.store import Phase2Store


class AutonomyBlockedError(MoltbookError):
    """Raised when policy blocks an outbound attempt."""


@dataclass(slots=True)
class ControlledAutonomyEngine:
    store: Phase2Store
    autonomy_store: AutonomyStore
    policy: AutonomyPolicy
    kill_switch: KillSwitch
    client: MoltbookClient | None = None
    dry_run: bool = True

    @classmethod
    def create(
        cls,
        store: Phase2Store,
        *,
        kill_switch: KillSwitch | None = None,
        dry_run: bool | None = None,
    ) -> "ControlledAutonomyEngine":
        policy = AutonomyPolicy.from_env()
        # Persist/restore experiment start & mode overlays from risk_state.
        saved = store.get_risk("autonomy_policy", {}) or {}
        if saved.get("experiment_started_at") and not policy.experiment_started_at:
            policy.experiment_started_at = saved["experiment_started_at"]
        if saved.get("mode") in {m.value for m in AutonomyMode}:
            # Env ACTIVE only if not suspended/fallback from prior incidents.
            if saved["mode"] in {
                AutonomyMode.SUSPENDED.value,
                AutonomyMode.READ_ONLY_FALLBACK.value,
            }:
                policy.mode = AutonomyMode(saved["mode"])
                policy.suspension_reason = saved.get("suspension_reason", "")
                policy.consecutive_errors = int(saved.get("consecutive_errors") or 0)
        dry = (
            dry_run
            if dry_run is not None
            else (os.getenv("MOLTBOOK_AUTONOMY_DRY_RUN", "true").lower() in {"1", "true", "yes", "on"})
        )
        return cls(
            store=store,
            autonomy_store=AutonomyStore(store),
            policy=policy,
            kill_switch=kill_switch or KillSwitch.from_env(),
            dry_run=dry,
        )

    def _persist_policy(self) -> None:
        self.store.set_risk("autonomy_policy", self.policy.snapshot())

    def status(self) -> dict[str, Any]:
        return {
            "kill_switch": self.kill_switch.snapshot(),
            "policy": self.policy.snapshot(),
            "dry_run": self.dry_run,
            "live_writes_enabled": bool(
                self.policy.mode is AutonomyMode.ACTIVE
                and self.policy.experiment_active()
                and not self.dry_run
                and not self.kill_switch.engaged
            ),
            "counters": {
                "create_post": self.autonomy_store.get_counter(
                    "create_post", window_hours=24
                ),
                "comment": self.autonomy_store.get_counter("comment", window_hours=24),
                "follow": self.autonomy_store.get_counter("follow", window_hours=24 * 7),
            },
            "content_generation_rules": CONTENT_GENERATION_RULES,
            "activation_ready_requires": [
                "MOLTBOOK_CONTROLLED_AUTONOMY=true",
                "MOLTBOOK_EXPERIMENT_STARTED_AT set (ISO UTC)",
                "kill switch off",
                "MOLTBOOK_AUTONOMY_DRY_RUN=false for live network writes",
                "final owner activation approval",
            ],
            "safe_to_activate": False,
            "safe_to_activate_note": (
                "Engine defaults remain inactive/dry-run. Owner must review the "
                "safety report and give separate final approval before activation."
            ),
        }

    def start_experiment_clock(self) -> dict[str, Any]:
        """Record experiment start; does not by itself enable autonomy."""
        if not self.policy.experiment_started_at:
            self.policy.experiment_started_at = utc_now_iso()
            self._persist_policy()
        return self.status()

    def _preflight(
        self,
        *,
        action: str,
        text: str,
        destination: str,
        inbound_context: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> str:
        if self.kill_switch.engaged:
            raise MoltbookOutboundDisabledError(
                f"Kill switch engaged: {self.kill_switch.reason}"
            )
        if self.policy.mode is AutonomyMode.SUSPENDED:
            raise MoltbookOutboundDisabledError(
                f"Autonomy suspended: {self.policy.suspension_reason}"
            )
        if self.policy.mode is AutonomyMode.READ_ONLY_FALLBACK:
            raise MoltbookOutboundDisabledError(
                f"Read-only fallback active: {self.policy.suspension_reason}"
            )
        if self.policy.mode is not AutonomyMode.ACTIVE:
            raise MoltbookOutboundDisabledError(
                "Controlled autonomy inactive or experiment window closed"
            )
        # Live writes require an open experiment window. Dry-run may proceed
        # before MOLTBOOK_EXPERIMENT_STARTED_AT is set (production verification).
        if not self.dry_run and not self.policy.experiment_active():
            raise MoltbookOutboundDisabledError(
                "Experiment window not started or closed; live writes blocked"
            )

        if self.autonomy_store.has_idempotency(idempotency_key):
            raise AutonomyBlockedError("duplicate_idempotency_key")

        verdict = qualify_outbound_content(
            action=action,
            text=text,
            destination=destination,
            inbound_context=inbound_context,
        )
        digest = content_hash({"action": action, "destination": destination, "payload": payload})
        if digest in self.autonomy_store.recent_content_hashes():
            verdict.block("duplicate_content_hash")

        # Credential exposure suspicion → immediate suspension (not just a block).
        secret_hits = scan_secrets_and_pii(text)
        if secret_hits or "secret_or_pii_detected" in verdict.reasons:
            self.policy.suspend_for_credential_exposure(
                "outbound payload matched secret/PII scanner"
            )
            self._persist_policy()
            self.autonomy_store.log_block(
                action=action,
                reasons=["credential_exposure_suspected", *verdict.reasons],
                payload_hash=digest,
                detail={"warnings": verdict.warnings + secret_hits},
            )
            self.store.append_audit(
                module="autonomy",
                action="suspended_credential_exposure",
                success=False,
                detail={"action": action},
            )
            raise MoltbookOutboundDisabledError(
                "Suspended due to suspected credential exposure"
            )

        if not verdict.allowed:
            self.autonomy_store.log_block(
                action=action,
                reasons=verdict.reasons,
                payload_hash=digest,
                detail={"warnings": verdict.warnings, "destination": destination},
            )
            self.store.append_audit(
                module="autonomy",
                action="blocked",
                success=False,
                detail={"action": action, "reasons": verdict.reasons},
            )
            raise AutonomyBlockedError(";".join(verdict.reasons))

        return digest

    def _limit_for(self, action: str) -> tuple[int, int]:
        """Return (limit, window_hours)."""
        if action == "create_post":
            return self.policy.limits.max_posts_per_24h, 24
        if action == "comment":
            return self.policy.limits.max_comments_per_24h, 24
        if action == "follow":
            return self.policy.limits.max_follows_per_7d, 24 * 7
        return 1, 24

    async def _client(self) -> MoltbookClient:
        if self.client is None:
            self.client = create_client()
        return self.client

    async def execute_post(
        self,
        *,
        submolt: str,
        title: str,
        content: str,
        idempotency_key: str | None = None,
        inbound_context: str = "",
    ) -> dict[str, Any]:
        action = OutboundAction.CREATE_POST.value
        payload = {"submolt": submolt, "title": title, "content": content}
        destination = f"submolt:{submolt}"
        key = idempotency_key or f"post-{content_hash(payload)}"
        text = f"{title}\n{content}"
        digest = self._preflight(
            action=action,
            text=text,
            destination=destination,
            inbound_context=inbound_context,
            idempotency_key=key,
            payload=payload,
        )
        limit, hours = self._limit_for(action)
        try:
            count = self.autonomy_store.increment_counter(
                action, limit=limit, window_hours=hours
            )
        except OverflowError as exc:
            self.autonomy_store.log_block(
                action=action, reasons=["quota_exceeded"], payload_hash=digest
            )
            raise AutonomyBlockedError(str(exc)) from exc

        self.store.append_audit(
            module="autonomy",
            action="pre_execute_create_post",
            success=True,
            detail={"content_hash": digest, "counter": count, "dry_run": self.dry_run},
        )

        if self.dry_run:
            result = {
                "dry_run": True,
                "published": False,
                "action": action,
                "destination": destination,
                "content_hash": digest,
                "url": None,
            }
            self.autonomy_store.log_action(
                action=action,
                destination=destination,
                content_hash=digest,
                idempotency_key=key,
                success=True,
                detail=result,
            )
            self.policy.record_success()
            self._persist_policy()
            return redact_value(result)

        # Live network write path (only when dry_run=false and autonomy active).
        try:
            client = await self._client()
            # Use low-level httpx through client settings to avoid Phase1 write stubs.
            headers = {
                "Authorization": f"Bearer {client.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": client.settings.user_agent,
            }
            async with httpx.AsyncClient(timeout=client.settings.timeout_seconds) as http:
                resp = await http.post(
                    f"{client.settings.base_url}/posts",
                    headers=headers,
                    json={
                        "submolt_name": submolt,
                        "title": title,
                        "content": content,
                        "type": "text",
                    },
                )
            body = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                raise MoltbookError(redact_text(f"post failed {resp.status_code}: {resp.text[:300]}"))
            post = body.get("post") if isinstance(body.get("post"), dict) else {}
            post_id = post.get("id")
            url = f"https://www.moltbook.com/post/{post_id}" if post_id else None
            # Verification challenge handling is intentionally NOT auto-solved here
            # without owner-approved solver path; if required, mark pending_verification.
            result = {
                "dry_run": False,
                "published": post.get("verification_status") in {None, "verified"},
                "pending_verification": bool(post.get("verification")),
                "action": action,
                "destination": destination,
                "content_hash": digest,
                "url": url,
                "post_id": post_id,
            }
            self.autonomy_store.log_action(
                action=action,
                destination=destination,
                content_hash=digest,
                idempotency_key=key,
                success=True,
                url=url,
                detail=redact_value(result),
            )
            self.store.append_audit(
                module="autonomy",
                action="post_execute_create_post",
                success=True,
                detail=redact_value({"url": url, "post_id": post_id}),
            )
            self.policy.record_success()
            self._persist_policy()
            return redact_value(result)
        except Exception as exc:  # noqa: BLE001
            self.policy.record_error()
            self._persist_policy()
            self.autonomy_store.log_action(
                action=action,
                destination=destination,
                content_hash=digest,
                idempotency_key=key + f"-fail-{uuid4()}",
                success=False,
                detail={"error": redact_text(str(exc))},
            )
            raise

    async def execute_comment(
        self,
        *,
        post_id: str,
        content: str,
        inbound_context: str = "",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        action = OutboundAction.COMMENT.value
        payload = {"post_id": post_id, "content": content}
        destination = f"post:{post_id}"
        key = idempotency_key or f"comment-{content_hash(payload)}"
        digest = self._preflight(
            action=action,
            text=content,
            destination=destination,
            inbound_context=inbound_context,
            idempotency_key=key,
            payload=payload,
        )
        limit, hours = self._limit_for(action)
        try:
            self.autonomy_store.increment_counter(
                action, limit=limit, window_hours=hours
            )
        except OverflowError as exc:
            self.autonomy_store.log_block(
                action=action, reasons=["quota_exceeded"], payload_hash=digest
            )
            raise AutonomyBlockedError(str(exc)) from exc

        if self.dry_run:
            result = {
                "dry_run": True,
                "published": False,
                "action": action,
                "destination": destination,
                "content_hash": digest,
                "url": f"https://www.moltbook.com/post/{post_id}",
            }
            self.autonomy_store.log_action(
                action=action,
                destination=destination,
                content_hash=digest,
                idempotency_key=key,
                success=True,
                url=result["url"],
                detail=result,
            )
            self.policy.record_success()
            self._persist_policy()
            return result

        # Live comment path
        try:
            client = await self._client()
            headers = {
                "Authorization": f"Bearer {client.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": client.settings.user_agent,
            }
            async with httpx.AsyncClient(timeout=client.settings.timeout_seconds) as http:
                resp = await http.post(
                    f"{client.settings.base_url}/posts/{post_id}/comments",
                    headers=headers,
                    json={"content": content},
                )
            if resp.status_code >= 400:
                raise MoltbookError(redact_text(f"comment failed {resp.status_code}"))
            result = {
                "dry_run": False,
                "published": True,
                "action": action,
                "destination": destination,
                "content_hash": digest,
                "url": f"https://www.moltbook.com/post/{post_id}",
            }
            self.autonomy_store.log_action(
                action=action,
                destination=destination,
                content_hash=digest,
                idempotency_key=key,
                success=True,
                url=result["url"],
                detail=result,
            )
            self.policy.record_success()
            self._persist_policy()
            return result
        except Exception as exc:  # noqa: BLE001
            self.policy.record_error()
            self._persist_policy()
            raise

    async def execute_follow(
        self,
        *,
        agent_name: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        action = OutboundAction.FOLLOW.value
        payload = {"agent_name": agent_name, "reason": reason}
        destination = f"agent:{agent_name}"
        key = idempotency_key or f"follow-{agent_name}"
        # Suspicious/spam account heuristics
        if detect_prompt_injection(agent_name) or detect_prompt_injection(reason):
            self.autonomy_store.log_block(
                action=action, reasons=["suspicious_follow_target"], detail=payload
            )
            raise AutonomyBlockedError("suspicious_follow_target")
        digest = self._preflight(
            action=action,
            text=reason,
            destination=destination,
            inbound_context="",
            idempotency_key=key,
            payload=payload,
        )
        limit, hours = self._limit_for(action)
        try:
            self.autonomy_store.increment_counter(
                action, limit=limit, window_hours=hours
            )
        except OverflowError as exc:
            self.autonomy_store.log_block(
                action=action, reasons=["quota_exceeded"], payload_hash=digest
            )
            raise AutonomyBlockedError(str(exc)) from exc

        result = {
            "dry_run": self.dry_run,
            "published": not self.dry_run,
            "action": action,
            "destination": destination,
            "content_hash": digest,
            "url": f"https://www.moltbook.com/u/{agent_name}",
        }
        if not self.dry_run:
            client = await self._client()
            headers = {
                "Authorization": f"Bearer {client.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": client.settings.user_agent,
            }
            async with httpx.AsyncClient(timeout=client.settings.timeout_seconds) as http:
                resp = await http.post(
                    f"{client.settings.base_url}/agents/{agent_name}/follow",
                    headers=headers,
                )
            if resp.status_code >= 400:
                self.policy.record_error()
                self._persist_policy()
                raise MoltbookError(redact_text(f"follow failed {resp.status_code}"))

        self.autonomy_store.log_action(
            action=action,
            destination=destination,
            content_hash=digest,
            idempotency_key=key,
            success=True,
            url=result["url"],
            detail=result,
        )
        self.policy.record_success()
        self._persist_policy()
        return result

    async def execute_delete(
        self,
        *,
        content_id: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Correct/delete own content for error, privacy, broken link, or misleading statement."""
        action = OutboundAction.DELETE_CONTENT.value
        allowed_reasons = ("error", "privacy", "broken_link", "misleading")
        if reason not in allowed_reasons:
            raise AutonomyBlockedError("delete_reason_not_authorized")
        payload = {"content_id": content_id, "reason": reason}
        destination = f"content:{content_id}"
        key = idempotency_key or f"delete-{content_id}-{reason}"
        digest = self._preflight(
            action=action,
            text=f"delete own content due to {reason}",
            destination=destination,
            inbound_context="",
            idempotency_key=key,
            payload=payload,
        )
        result = {
            "dry_run": self.dry_run,
            "published": not self.dry_run,
            "action": action,
            "destination": destination,
            "content_hash": digest,
            "url": None,
            "reason": reason,
        }
        if not self.dry_run:
            client = await self._client()
            headers = {
                "Authorization": f"Bearer {client.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": client.settings.user_agent,
            }
            async with httpx.AsyncClient(timeout=client.settings.timeout_seconds) as http:
                resp = await http.delete(
                    f"{client.settings.base_url}/posts/{content_id}",
                    headers=headers,
                )
            if resp.status_code >= 400:
                self.policy.record_error()
                self._persist_policy()
                raise MoltbookError(redact_text(f"delete failed {resp.status_code}"))
        self.autonomy_store.log_action(
            action=action,
            destination=destination,
            content_hash=digest,
            idempotency_key=key,
            success=True,
            detail=result,
        )
        self.policy.record_success()
        self._persist_policy()
        return result

    def alert_owner_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        """Alert owner immediately for a credible YaliTek lead (no outbound publish)."""
        lead_id = str(lead.get("lead_id") or "unknown")
        detail = {
            "lead_id": lead_id,
            "service": lead.get("relevant_service"),
            "source_url": lead.get("source_url"),
            "confidence": lead.get("confidence_score"),
            "suggested_response": lead.get("suggested_response"),
            "requires_owner_before": CONTENT_GENERATION_RULES["leads"][
                "requires_owner_approval"
            ],
        }
        self.autonomy_store.log_lead_alert(lead_id, detail)
        self.store.append_audit(
            module="autonomy",
            action="lead_alert",
            success=True,
            detail=redact_value(detail),
        )
        return detail

    def build_daily_report(self) -> dict[str, Any]:
        since = utc_now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        actions = self.autonomy_store.list_actions_since(since)
        blocks = self.autonomy_store.list_blocks_since(since)
        alerts = self.autonomy_store.list_lead_alerts_since(since)
        leads = self.store.list_leads()
        report = {
            "date": utc_now().strftime("%Y-%m-%d"),
            "posts_comments_follows": [
                {
                    "action": a["action"],
                    "url": a.get("url"),
                    "destination": a["destination"],
                    "success": a["success"],
                    "timestamp": a["timestamp"],
                }
                for a in actions
            ],
            "engagement_received": "not_fetched_in_this_build",
            "leads_discovered": [
                {
                    "lead_id": lead["lead_id"],
                    "service": lead["relevant_service"],
                    "source_url": lead["source_url"],
                    "confidence": lead["confidence_score"],
                    "approval_status": lead["approval_status"],
                }
                for lead in leads
            ],
            "lead_alerts": alerts,
            "actions_blocked": [
                {"action": b["action"], "reasons": b["reasons"], "timestamp": b["timestamp"]}
                for b in blocks
            ],
            "limits_and_risk": self.status(),
            "recommended_owner_decisions": [
                "Review any leads with confidence >= 0.7",
                "Approve moving qualified leads to email/consultation if appropriate",
                "Confirm whether dry_run should remain enabled",
                "Do not expand autonomy permissions from missed targets",
            ],
            "crypto_boundary": "Paper trading only; no live trading authorized",
        }
        self.autonomy_store.save_daily_report(report["date"], report)
        self.store.append_audit(
            module="autonomy",
            action="daily_report",
            success=True,
            detail={"date": report["date"], "actions": len(actions), "blocks": len(blocks)},
        )
        return report
