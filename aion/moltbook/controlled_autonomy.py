"""Controlled Moltbook outbound executor for the 14-day experiment.

Default: inactive. Set MOLTBOOK_CONTROLLED_AUTONOMY=true only after final owner
activation approval. Even when active, every outbound payload is scanned,
quota-checked, paced, hashed, idempotent, and audited before/after execution.

Quotas are ceilings, not targets. Platform rate limits always override owner caps.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from aion.moltbook.approval import OutboundAction
from aion.moltbook.autonomy_policy import (
    AutonomyMode,
    AutonomyPolicy,
    QuotaProfile,
    content_generation_rules,
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
from aion.moltbook.verification import verify_content


class AutonomyBlockedError(MoltbookError):
    """Raised when policy blocks an outbound attempt."""


def _parse_retry_after(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    try:
        body = resp.json() if resp.content else {}
    except Exception:  # noqa: BLE001
        body = {}
    if isinstance(body, dict):
        for key in ("retry_after_seconds", "retry_after", "retryAfter"):
            if body.get(key) is not None:
                try:
                    return float(body[key])
                except (TypeError, ValueError):
                    continue
    return None


def _looks_like_platform_warning(status_code: int, body_text: str) -> bool:
    if status_code in {401, 403}:
        return True
    lowered = (body_text or "").lower()
    return bool(
        re.search(
            r"(moderat|warning|suspend|ban|credential|unauthorized|forbidden|"
            r"terms of service|tos violat)",
            lowered,
        )
    )


def _extract_account(destination: str, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit.strip().lstrip("@").lower()
    if destination.startswith("agent:"):
        return destination.split(":", 1)[1].strip().lower()
    return None


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
        saved = store.get_risk("autonomy_policy", {}) or {}
        if saved.get("experiment_started_at") and not policy.experiment_started_at:
            policy.experiment_started_at = saved["experiment_started_at"]
        if saved.get("mode") in {m.value for m in AutonomyMode}:
            if saved["mode"] in {
                AutonomyMode.SUSPENDED.value,
                AutonomyMode.READ_ONLY_FALLBACK.value,
            }:
                policy.mode = AutonomyMode(saved["mode"])
                policy.suspension_reason = saved.get("suspension_reason", "")
                policy.consecutive_errors = int(saved.get("consecutive_errors") or 0)
        # Restore quota reduction / backoff across restarts (do not reset counters).
        if saved.get("quota_profile") == QuotaProfile.REDUCED.value:
            policy.reduce_quotas(
                saved.get("quota_reduction_reason") or "restored_reduced_profile"
            )
            policy.quota_reduced_at = saved.get("quota_reduced_at") or policy.quota_reduced_at
        policy.rate_limit_streak = int(saved.get("rate_limit_streak") or 0)
        policy.platform_backoff_until = saved.get("platform_backoff_until")
        policy.negative_signal_count = int(saved.get("negative_signal_count") or 0)
        dry = (
            dry_run
            if dry_run is not None
            else (
                os.getenv("MOLTBOOK_AUTONOMY_DRY_RUN", "true").lower()
                in {"1", "true", "yes", "on"}
            )
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
        eff = self.policy.effective_limits()
        availability = self.autonomy_store.quota_availability(eff)
        return {
            "kill_switch": self.kill_switch.snapshot(),
            "policy": self.policy.snapshot(),
            "dry_run": self.dry_run,
            "live_writes_enabled": bool(
                self.policy.mode is AutonomyMode.ACTIVE
                and self.policy.experiment_active()
                and not self.dry_run
                and not self.kill_switch.engaged
                and not self.policy.platform_backoff_active()
            ),
            "counters": {
                "create_post": availability["create_post"],
                "comment": availability["comment"],
                "follow": availability["follow"],
            },
            "quota_availability": availability,
            "automatic_quota_reduction": {
                "active": self.policy.quota_profile is QuotaProfile.REDUCED,
                "reduced_at": self.policy.quota_reduced_at,
                "reason": self.policy.quota_reduction_reason,
            },
            "platform_backoff_until": self.policy.platform_backoff_until,
            "content_generation_rules": content_generation_rules(eff),
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
            "quotas_are_ceilings_not_targets": True,
        }

    def start_experiment_clock(self) -> dict[str, Any]:
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
        if not self.dry_run and not self.policy.experiment_active():
            raise MoltbookOutboundDisabledError(
                "Experiment window not started or closed; live writes blocked"
            )
        if self.policy.platform_backoff_active():
            raise MoltbookOutboundDisabledError(
                f"Platform backoff active until {self.policy.platform_backoff_until}"
            )

        if self.autonomy_store.has_idempotency(idempotency_key):
            raise AutonomyBlockedError("duplicate_idempotency_key")

        recent_texts = self.autonomy_store.recent_texts()
        recent_topics = self.autonomy_store.recent_post_topics()
        verdict = qualify_outbound_content(
            action=action,
            text=text,
            destination=destination,
            inbound_context=inbound_context,
            recent_texts=recent_texts,
            recent_post_topics=recent_topics,
            limits=self.policy.effective_limits(),
        )
        digest = content_hash(
            {"action": action, "destination": destination, "payload": payload}
        )
        if digest in self.autonomy_store.recent_content_hashes():
            verdict.block("duplicate_content_hash")

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
                detail={
                    "warnings": verdict.warnings,
                    "destination": destination,
                    "relevance_score": verdict.relevance_score,
                    "usefulness_score": verdict.usefulness_score,
                    "quality_skips": verdict.quality_skips,
                },
            )
            self.store.append_audit(
                module="autonomy",
                action="blocked",
                success=False,
                detail={
                    "action": action,
                    "reasons": verdict.reasons,
                    "quality_skips": verdict.quality_skips,
                },
            )
            raise AutonomyBlockedError(";".join(verdict.reasons))

        return digest

    def _limit_for(self, action: str) -> tuple[int, int]:
        lim = self.policy.effective_limits()
        if action == "create_post":
            return lim.max_posts_per_24h, 24
        if action == "comment":
            return lim.max_comments_per_24h, 24
        if action == "follow":
            return lim.max_follows_per_7d, 24 * 7
        return 1, 24

    def _reserve_slot(
        self,
        *,
        action: str,
        digest: str,
        account: str | None = None,
        solicited: bool = False,
    ) -> int:
        lim = self.policy.effective_limits()
        try:
            self.autonomy_store.assert_pacing(action, lim)
            self.autonomy_store.assert_account_cap(
                account, limits=lim, solicited=solicited
            )
            limit, hours = self._limit_for(action)
            count = self.autonomy_store.increment_counter(
                action, limit=limit, window_hours=hours
            )
            return count
        except OverflowError as exc:
            reason = str(exc)
            block_reason = "quota_exceeded"
            if reason.startswith("pacing_"):
                block_reason = reason.split(":")[0]
            elif reason.startswith("per_account_cap"):
                block_reason = "per_account_cap"
            self.autonomy_store.log_block(
                action=action,
                reasons=[block_reason, reason],
                payload_hash=digest,
                detail={"account": account},
            )
            raise AutonomyBlockedError(reason) from exc

    async def _client(self) -> MoltbookClient:
        if self.client is None:
            self.client = create_client()
        return self.client

    def _handle_http_failure(
        self, *, action: str, resp: httpx.Response | None, exc: Exception | None = None
    ) -> None:
        status = resp.status_code if resp is not None else 0
        text = ""
        if resp is not None:
            try:
                text = resp.text[:500]
            except Exception:  # noqa: BLE001
                text = ""
        retry_after = _parse_retry_after(resp) if resp is not None else None
        if status == 429 or (exc and "429" in str(exc)):
            self.autonomy_store.log_rate_limit(
                action=action,
                status_code=status or 429,
                retry_after_seconds=retry_after,
                detail={"body": redact_text(text)},
            )
            self.policy.record_rate_limit_response(retry_after_seconds=retry_after)
            self._persist_policy()
            return
        if resp is not None and _looks_like_platform_warning(status, text):
            self.autonomy_store.log_rate_limit(
                action=action,
                status_code=status,
                retry_after_seconds=retry_after,
                detail={"body": redact_text(text), "kind": "platform_warning"},
            )
            self.policy.record_platform_warning(redact_text(text)[:200])
            self._persist_policy()
            return
        self.policy.record_error()
        self._persist_policy()

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
        count = self._reserve_slot(action=action, digest=digest)

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
                text_norm=text,
            )
            self.policy.record_success()
            self._persist_policy()
            return redact_value(result)

        try:
            client = await self._client()
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
                self._handle_http_failure(action=action, resp=resp)
                raise MoltbookError(
                    redact_text(f"post failed {resp.status_code}: {resp.text[:300]}")
                )
            post = body.get("post") if isinstance(body.get("post"), dict) else {}
            post_id = post.get("id")
            url = f"https://www.moltbook.com/post/{post_id}" if post_id else None
            verification = (
                post.get("verification")
                if isinstance(post.get("verification"), dict)
                else None
            )
            pending = bool(verification) or post.get("verification_status") == "pending"
            if pending and verification:
                await verify_content(
                    base_url=client.settings.base_url,
                    headers=headers,
                    verification=verification,
                    timeout=client.settings.timeout_seconds,
                )
                pending = False
            result = {
                "dry_run": False,
                "published": not pending,
                "pending_verification": pending,
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
                text_norm=text,
            )
            self.store.append_audit(
                module="autonomy",
                action="post_execute_create_post",
                success=True,
                detail=redact_value(
                    {"url": url, "post_id": post_id, "published": not pending}
                ),
            )
            self.policy.record_success()
            self._persist_policy()
            return redact_value(result)
        except Exception as exc:  # noqa: BLE001
            self.autonomy_store.refund_last_quota(action)
            if not isinstance(exc, MoltbookError):
                self.policy.record_error()
                self._persist_policy()
            self.autonomy_store.log_action(
                action=action,
                destination=destination,
                content_hash=digest,
                idempotency_key=key + f"-fail-{uuid4()}",
                success=False,
                detail={"error": redact_text(str(exc))},
                text_norm=text,
            )
            raise

    async def execute_comment(
        self,
        *,
        post_id: str,
        content: str,
        inbound_context: str = "",
        idempotency_key: str | None = None,
        target_account: str | None = None,
        solicited: bool = False,
    ) -> dict[str, Any]:
        action = OutboundAction.COMMENT.value
        payload = {"post_id": post_id, "content": content}
        destination = f"post:{post_id}"
        key = idempotency_key or f"comment-{content_hash(payload)}"
        account = _extract_account(destination, target_account)
        digest = self._preflight(
            action=action,
            text=content,
            destination=destination,
            inbound_context=inbound_context,
            idempotency_key=key,
            payload=payload,
        )
        self._reserve_slot(
            action=action, digest=digest, account=account, solicited=solicited
        )

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
                text_norm=content,
                account=account,
            )
            if account:
                self.autonomy_store.record_account_interaction(
                    account, action=action, solicited=solicited
                )
            self.policy.record_success()
            self._persist_policy()
            return result

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
                self._handle_http_failure(action=action, resp=resp)
                raise MoltbookError(redact_text(f"comment failed {resp.status_code}"))
            body = resp.json() if resp.content else {}
            comment = body.get("comment") if isinstance(body.get("comment"), dict) else {}
            verification = (
                comment.get("verification")
                if isinstance(comment.get("verification"), dict)
                else body.get("verification")
                if isinstance(body.get("verification"), dict)
                else None
            )
            pending = bool(verification) or comment.get("verification_status") == "pending"
            if pending:
                if not verification:
                    raise MoltbookError(
                        "Comment pending verification but challenge payload missing"
                    )
                await verify_content(
                    base_url=client.settings.base_url,
                    headers=headers,
                    verification=verification,
                    timeout=client.settings.timeout_seconds,
                )
                pending = False
            result = {
                "dry_run": False,
                "published": not pending,
                "pending_verification": pending,
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
                text_norm=content,
                account=account,
            )
            if account:
                self.autonomy_store.record_account_interaction(
                    account, action=action, solicited=solicited
                )
            self.policy.record_success()
            self._persist_policy()
            return result
        except Exception as exc:  # noqa: BLE001
            self.autonomy_store.refund_last_quota(action)
            if not isinstance(exc, MoltbookError):
                self.policy.record_error()
                self._persist_policy()
            raise

    async def execute_follow(
        self,
        *,
        agent_name: str,
        reason: str,
        idempotency_key: str | None = None,
        solicited: bool = False,
    ) -> dict[str, Any]:
        action = OutboundAction.FOLLOW.value
        payload = {"agent_name": agent_name, "reason": reason}
        destination = f"agent:{agent_name}"
        key = idempotency_key or f"follow-{agent_name}"
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
        account = agent_name.strip().lstrip("@").lower()
        self._reserve_slot(
            action=action, digest=digest, account=account, solicited=solicited
        )

        result = {
            "dry_run": self.dry_run,
            "published": not self.dry_run,
            "action": action,
            "destination": destination,
            "content_hash": digest,
            "url": f"https://www.moltbook.com/u/{agent_name}",
            "relevance_reason": reason,
        }
        if not self.dry_run:
            try:
                client = await self._client()
                headers = {
                    "Authorization": f"Bearer {client.settings.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": client.settings.user_agent,
                }
                async with httpx.AsyncClient(
                    timeout=client.settings.timeout_seconds
                ) as http:
                    resp = await http.post(
                        f"{client.settings.base_url}/agents/{agent_name}/follow",
                        headers=headers,
                    )
                if resp.status_code >= 400:
                    self._handle_http_failure(action=action, resp=resp)
                    raise MoltbookError(redact_text(f"follow failed {resp.status_code}"))
            except Exception:
                self.autonomy_store.refund_last_quota(action)
                raise

        self.autonomy_store.log_action(
            action=action,
            destination=destination,
            content_hash=digest,
            idempotency_key=key,
            success=True,
            url=result["url"],
            detail=result,
            text_norm=reason,
            account=account,
        )
        self.autonomy_store.record_account_interaction(
            account, action=action, solicited=solicited
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
                self._handle_http_failure(action=action, resp=resp)
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
        lead_id = str(lead.get("lead_id") or "unknown")
        rules = content_generation_rules(self.policy.effective_limits())
        detail = {
            "lead_id": lead_id,
            "service": lead.get("relevant_service"),
            "source_url": lead.get("source_url"),
            "confidence": lead.get("confidence_score"),
            "suggested_response": lead.get("suggested_response"),
            "requires_owner_before": rules["leads"]["requires_owner_approval"],
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
        rate_limits = self.autonomy_store.list_rate_limits_since(since)
        follows = self.autonomy_store.list_follows_since(since)
        leads = self.store.list_leads()
        quality_skips = [
            {
                "action": b["action"],
                "reasons": b["reasons"],
                "timestamp": b["timestamp"],
                "detail": b.get("detail"),
            }
            for b in blocks
            if any(
                r.startswith(
                    (
                        "semantic_duplicate",
                        "relevance_",
                        "usefulness_",
                        "topic_diversity",
                        "generic_praise",
                        "engagement_bait",
                        "comment_lacks",
                        "follow_relevance",
                        "per_account",
                        "pacing_",
                    )
                )
                or r
                in {
                    "generic_praise_forbidden",
                    "engagement_bait_forbidden",
                    "topic_not_in_allowlist",
                    "comment_lacks_concrete_contribution",
                    "duplicate_content_hash",
                }
                for r in b["reasons"]
            )
        ]
        engagement_by_content: dict[str, Any] = {}
        for a in actions:
            if a["action"] in {"create_post", "comment"} and a.get("url"):
                engagement_by_content[a["url"]] = {
                    "action": a["action"],
                    "destination": a["destination"],
                    "success": a["success"],
                    "timestamp": a["timestamp"],
                }
        report = {
            "date": utc_now().strftime("%Y-%m-%d"),
            "quota_availability": self.autonomy_store.quota_availability(
                self.policy.effective_limits()
            ),
            "automatic_quota_reduction": {
                "active": self.policy.quota_profile is QuotaProfile.REDUCED,
                "reduced_at": self.policy.quota_reduced_at,
                "reason": self.policy.quota_reduction_reason,
            },
            "posts_comments_follows": [
                {
                    "action": a["action"],
                    "url": a.get("url"),
                    "destination": a["destination"],
                    "account": a.get("account"),
                    "success": a["success"],
                    "timestamp": a["timestamp"],
                }
                for a in actions
            ],
            "engagement_by_post_and_comment": engagement_by_content,
            "accounts_followed": [
                {
                    "account": f.get("account") or f["destination"],
                    "url": f.get("url"),
                    "relevance_reason": (f.get("detail") or {}).get("relevance_reason"),
                    "timestamp": f["timestamp"],
                    "success": f["success"],
                }
                for f in follows
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
                {
                    "action": b["action"],
                    "reasons": b["reasons"],
                    "timestamp": b["timestamp"],
                }
                for b in blocks
            ],
            "actions_skipped_for_quality": quality_skips,
            "rate_limit_responses": rate_limits,
            "negative_feedback_or_moderation": [
                r
                for r in rate_limits
                if (r.get("detail") or {}).get("kind") == "platform_warning"
            ]
            + (
                [
                    {
                        "signal": "quota_reduced",
                        "reason": self.policy.quota_reduction_reason,
                        "at": self.policy.quota_reduced_at,
                    }
                ]
                if self.policy.quota_profile is QuotaProfile.REDUCED
                else []
            ),
            "limits_and_risk": self.status(),
            "recommended_owner_decisions": [
                "Review any leads with confidence >= 0.7",
                "Approve moving qualified leads to email/consultation if appropriate",
                "Quotas are ceilings — do not treat unused slots as missed targets",
                "Do not expand autonomy permissions from missed targets",
                "DMs / pricing / contracts / live crypto still require separate approval",
            ],
            "crypto_boundary": "Paper trading only; no live trading authorized",
        }
        self.autonomy_store.save_daily_report(report["date"], report)
        self.store.append_audit(
            module="autonomy",
            action="daily_report",
            success=True,
            detail={
                "date": report["date"],
                "actions": len(actions),
                "blocks": len(blocks),
                "quota_profile": self.policy.quota_profile.value,
            },
        )
        return report
