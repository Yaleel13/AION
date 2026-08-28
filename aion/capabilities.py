"""Truthful capability-level permission registry for AION.

A capability being configured never implies broad autonomy. Read, propose,
approve, and execute are reported separately and default closed.
"""
from __future__ import annotations

import os
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


def capability_registry() -> dict[str, Any]:
    runtime = build_runtime_status()
    storage_ready = bool(runtime["storage"]["configured"])
    owner_ready = bool(runtime["operations"]["owner_token_configured"])
    terminal_ready = bool(runtime["operations"]["terminal_executor_connected"])
    moltbook_configured = bool(runtime["moltbook"]["configured"])
    moltbook_outbound = bool(runtime["moltbook"]["outbound_enabled"])
    moltbook_execute = bool(runtime["moltbook"]["execute_enabled"])
    github_credential_present = bool(
        os.getenv("AION_GITHUB_TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or os.getenv("GITHUB_APP_INSTALLATION_TOKEN")
    )

    capabilities = {
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
    }
    return {
        "ok": True,
        "policy": "capability-level-least-privilege",
        "global_autonomy_switch": False,
        "capabilities": capabilities,
    }
