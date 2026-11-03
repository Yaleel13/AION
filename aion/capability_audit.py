"""Request-scoped capability evidence in the existing owner audit history.

Only fixed route/capability labels and scalar outcomes are recorded. Audit
storage is best effort, as on diagnostic routes it must not change availability
or interrupt process ownership and cleanup.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class CapabilityAudit:
    capability: str
    permission: str
    path: str
    method: str
    request_id: str = field(default_factory=lambda: uuid4().hex)
    policy_decision: str = "not_evaluated"
    job_started: bool = False
    outcome: str | None = None

    def record(self, event: str, *, success: bool, **extra) -> None:
        detail = {
            "request_id": self.request_id, "capability": self.capability,
            "permission": self.permission, "path": self.path, "method": self.method,
            "policy_decision": self.policy_decision, "job_started": self.job_started,
            **extra,
        }
        try:
            from aion.phase2_services import get_services

            get_services().store.append_audit(
                module="capabilities", action=f"capability.{event}",
                success=success, detail=detail,
            )
        except Exception:
            # Never log exception text: database/provider errors can contain secrets.
            try:
                logger.warning("Capability audit storage unavailable")
            except Exception:
                # A failed logging handler is also an audit sink failure. In
                # particular it must not lose an acquired subprocess handle.
                pass


_current: ContextVar[CapabilityAudit | None] = ContextVar("capability_audit", default=None)


def policy_decision(code: str | None = None) -> None:
    if audit := _current.get():
        audit.policy_decision = "allowed" if code is None else (
            "unavailable" if code == "policy_unavailable" else "denied"
        )
        audit.record("policy", success=code is None)


def job_started() -> None:
    if (audit := _current.get()) and not audit.job_started:
        audit.job_started = True
        audit.record("job_started", success=True)


def handler_result(result: dict) -> None:
    if audit := _current.get():
        if audit.capability == "runtime.syntax":
            status = result.get("status")
            audit.outcome = status if status in {"succeeded", "failed", "timeout", "unavailable"} else "failed"
        else:
            audit.outcome = "succeeded"


class CapabilityAuditMiddleware:
    """Transparent ASGI wrapper; does not consume request/disconnect messages."""

    routes = {
        "/runtime/status": ("runtime_status", "read"),
        "/owner/runtime/status": ("runtime_status", "read"),
        "/local-executive/validate": ("runtime.syntax", "execute"),
    }

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        labels = self.routes.get(scope.get("path"))
        if scope["type"] != "http" or labels is None:
            return await self.app(scope, receive, send)
        audit = CapabilityAudit(*labels, path=scope["path"], method=(
            scope["method"] if scope["method"] in {"GET", "POST"} else "OTHER"
        ))
        token = _current.set(audit)
        status = 500

        async def send_response(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message = {**message, "headers": [
                    *message.get("headers", []),
                    (b"x-aion-request-id", audit.request_id.encode("ascii")),
                ]}
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        except asyncio.CancelledError:
            audit.outcome = "cancelled"
            raise
        finally:
            outcome = audit.outcome
            if status == 499:
                outcome = "cancelled"
            if outcome is None:
                outcome = "denied" if audit.policy_decision == "denied" else (
                    "policy_unavailable" if audit.policy_decision == "unavailable" else (
                        "rejected" if status < 500 else "failed"
                    )
                )
            try:
                audit.record("outcome", success=outcome == "succeeded", outcome=outcome, status_code=status)
            finally:
                _current.reset(token)
