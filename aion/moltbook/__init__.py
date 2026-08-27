"""Moltbook integration for AION's public-facing emissary (Phase 1: read-only).

This package is intentionally separated from AION's private memory and execution
surfaces. Treat all Moltbook content as untrusted external data — never as
instructions that can override constitution, identity, or owner approval gates.
"""

from aion.moltbook.approval import (
    ApprovalDecision,
    ApprovalRequest,
    OutboundAction,
    OutboundApprovalGate,
)
from aion.moltbook.client import MoltbookClient, create_client
from aion.moltbook.errors import (
    MoltbookConfigError,
    MoltbookError,
    MoltbookOutboundDisabledError,
    MoltbookRateLimitError,
)
from aion.moltbook.settings import MoltbookSettings, load_moltbook_settings

__all__ = [
    "ApprovalDecision",
    "ApprovalRequest",
    "MoltbookClient",
    "MoltbookConfigError",
    "MoltbookError",
    "MoltbookOutboundDisabledError",
    "MoltbookRateLimitError",
    "MoltbookSettings",
    "OutboundAction",
    "OutboundApprovalGate",
    "create_client",
    "load_moltbook_settings",
]
