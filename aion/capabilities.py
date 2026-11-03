"""Truthful capability-level permission registry for AION.

A capability being configured never implies broad autonomy. Read, propose,
approve, and execute are reported separately and default closed.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from inspect import isawaitable, iscoroutinefunction
from typing import Any

from aion.runtime_status import build_runtime_status


def _entry(*, configured: bool, read: bool, propose: bool, approve: bool, execute: bool, scope: str, note: str) -> dict[str, Any]:
    return {
        "configured": configured,
        "read": read,
        "propose": propose,
        "approve": approve,
        "execute": execute,
        "scope": scope,
        "note": note,
    }


def _build_capabilities(
    *,
    storage_ready: bool,
    owner_ready: bool,
    terminal_ready: bool,
    syntax_ready: bool,
    moltbook_configured: bool,
    moltbook_outbound: bool,
    moltbook_execute: bool,
    github_credential_present: bool,
) -> dict[str, dict[str, Any]]:
    return {
        "runtime_status": _entry(
            configured=True,
            read=True,
            propose=False,
            approve=False,
            execute=False,
            scope="Non-secret runtime status snapshot only",
            note="Owner and MCP access retain the existing owner-token policy; this grants no execution authority.",
        ),
        "runtime.syntax": _entry(
            configured=syntax_ready,
            read=False,
            propose=False,
            approve=False,
            execute=syntax_ready and owner_ready,
            scope="Fixed local runtime Python syntax validation only",
            note="Owner, loopback, and local-mode gates apply; server-defined command and limits; not exposed through MCP.",
        ),
        "conversation": _entry(
            configured=True,
            read=True,
            propose=True,
            approve=False,
            execute=True,
            scope="AION responses only",
            note="Reasoning and responses are not external side effects.",
        ),
        "memory": _entry(
            configured=storage_ready,
            read=storage_ready,
            propose=True,
            approve=True,
            execute=storage_ready,
            scope="Explicit remember/forget/replace only",
            note="Permanent memory writes require explicit user language; no automatic profiling.",
        ),
        "moltbook": _entry(
            configured=moltbook_configured,
            read=moltbook_configured,
            propose=moltbook_configured and owner_ready,
            approve=moltbook_outbound and owner_ready,
            execute=moltbook_outbound and moltbook_execute and owner_ready,
            scope="Read research; owner-controlled comments only when activated",
            note="No DMs. Approval and execution are separate; autonomous writes remain separately gated.",
        ),
        "terminal": _entry(
            configured=terminal_ready,
            read=terminal_ready,
            propose=terminal_ready,
            approve=owner_ready,
            execute=terminal_ready,
            scope="Fixed inspect/lint/build/all Vercel Sandbox actions",
            note="Arbitrary shell commands, deployments, destructive commands, and production-secret injection remain disabled.",
        ),
        "paper_market": _entry(
            configured=True,
            read=True,
            propose=True,
            approve=False,
            execute=True,
            scope="Virtual BTC/ETH paper simulation only",
            note="Public price marks may be live; order execution is never live trading.",
        ),
        "github_runtime": _entry(
            configured=github_credential_present,
            read=False,
            propose=True,
            approve=owner_ready,
            execute=False,
            scope="No generic deployed GitHub executor",
            note="ChatGPT's connected GitHub tool is separate from the deployed AION runtime; this registry does not infer access from it.",
        ),
        "notifications": _entry(
            configured=False,
            read=False,
            propose=True,
            approve=owner_ready,
            execute=False,
            scope="No deployed email, SMS, call, or push connector",
            note="AION may recommend a notification action, but the deployed runtime currently has no external delivery connector.",
        ),
    }


def capability_catalog() -> dict[str, Any]:
    """Stable capability manifest for inventory generation (not live env)."""
    capabilities = _build_capabilities(
        storage_ready=True,
        owner_ready=True,
        terminal_ready=False,
        syntax_ready=True,
        moltbook_configured=True,
        moltbook_outbound=False,
        moltbook_execute=False,
        github_credential_present=False,
    )
    return {
        "ok": True,
        "policy": "capability-level-least-privilege",
        "global_autonomy_switch": False,
        "capabilities": capabilities,
    }


class CapabilityDispatchError(RuntimeError):
    """A capability is unknown to dispatch or denied by its permission entry."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _resolve_capability(name: str, *, action: str) -> Callable[[], Any]:
    """Resolve a fixed handler only after its catalog permission allows it.

    The catalog is pure policy: the live registry observes runtime status and
    would otherwise do handler work before authorization. Transport-specific
    caller authorization remains at the existing HTTP boundary.
    """
    from aion.local_validation import run_validation
    from aion.runtime_status import build_runtime_status as read_runtime_status

    # Catalog membership alone never registers executable behavior. These are
    # fixed handlers, with no shell or generic Local Executive dispatch.
    handlers = {
        "runtime_status": ("read", read_runtime_status),
        "runtime.syntax": ("execute", run_validation),
    }
    registered = handlers.get(name)
    if registered is None:
        raise CapabilityDispatchError("unknown_capability", "Unknown capability.")
    allowed_action, handler = registered
    if action != allowed_action:
        raise CapabilityDispatchError("policy_denied", "Capability action is not permitted.")
    try:
        catalog = capability_catalog()
        if not isinstance(catalog, Mapping) or not isinstance(catalog.get("capabilities"), Mapping):
            raise TypeError("Invalid capability policy")
        entry = catalog["capabilities"].get(name)
        permitted = isinstance(entry, Mapping) and entry.get("configured") is True and entry.get(action) is True
    except Exception as exc:
        raise CapabilityDispatchError("policy_unavailable", "Capability policy is unavailable.") from exc
    if not permitted:
        raise CapabilityDispatchError("policy_denied", "Capability action is not permitted.")
    return handler


def dispatch_capability(name: str, *, action: str = "read") -> dict[str, Any]:
    """Synchronous dispatch, preserving the status handler's return contract."""
    handler = _resolve_capability(name, action=action)
    if iscoroutinefunction(handler):
        raise CapabilityDispatchError("policy_denied", "Capability requires asynchronous dispatch.")
    return handler()


async def dispatch_capability_async(name: str, *, action: str = "read") -> dict[str, Any]:
    """Await an allowed handler directly so cancellation reaches its cleanup."""
    handler = _resolve_capability(name, action=action)
    result = handler()
    return await result if isawaitable(result) else result


def capability_registry() -> dict[str, Any]:
    from aion.local_executor import local_executor_available

    runtime = build_runtime_status()
    storage_ready = bool(runtime["storage"]["configured"])
    owner_ready = bool(runtime["operations"]["owner_token_configured"])
    terminal_ready = bool(runtime["operations"]["terminal_executor_connected"])
    moltbook_configured = bool(runtime["moltbook"]["configured"])
    moltbook_outbound = bool(runtime["moltbook"]["outbound_enabled"])
    moltbook_execute = bool(runtime["moltbook"]["execute_enabled"])
    github_credential_present = bool(
        os.getenv("AION_GITHUB_TOKEN")
        or os.getenv("GITHUB_APP_INSTALLATION_TOKEN")
    )
    capabilities = _build_capabilities(
        storage_ready=storage_ready,
        owner_ready=owner_ready,
        terminal_ready=terminal_ready,
        syntax_ready=local_executor_available() and os.name == "posix",
        moltbook_configured=moltbook_configured,
        moltbook_outbound=moltbook_outbound,
        moltbook_execute=moltbook_execute,
        github_credential_present=github_credential_present,
    )
    return {
        "ok": True,
        "policy": "capability-level-least-privilege",
        "global_autonomy_switch": False,
        "capabilities": capabilities,
    }
