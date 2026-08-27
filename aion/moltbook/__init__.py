"""Moltbook integration for AION's public-facing emissary.

Phase 1: read-only client foundation.
Phase 2: controlled growth via approval tokens, drafts, leads, and reporting.
Treat all Moltbook content as untrusted external data.
"""

from aion.moltbook.approval import (
    ApprovalDecision,
    ApprovalRequest,
    OutboundAction,
    OutboundApprovalGate,
    Phase2ApprovalGate,
)
from aion.moltbook.autonomy_policy import CONTENT_GENERATION_RULES, AutonomyPolicy
from aion.moltbook.client import MoltbookClient, create_client
from aion.moltbook.controlled_autonomy import ControlledAutonomyEngine
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
    "CONTENT_GENERATION_RULES",
    "AutonomyPolicy",
    "ControlledAutonomyEngine",
    "MoltbookClient",
    "MoltbookConfigError",
    "MoltbookError",
    "MoltbookOutboundDisabledError",
    "MoltbookRateLimitError",
    "MoltbookSettings",
    "OutboundAction",
    "OutboundApprovalGate",
    "Phase2ApprovalGate",
    "create_client",
    "load_moltbook_settings",
]
