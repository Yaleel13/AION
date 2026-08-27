"""Shared Phase 2 security primitives for Moltbook / leads / paper trading."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from aion.moltbook.redact import redact_value

# Heuristic patterns that often appear in prompt-injection payloads.
_INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore (all |any )?(previous|prior|above) (instructions|rules)\b"),
    re.compile(r"(?i)\bdisregard (your|the) (system|developer) (prompt|instructions)\b"),
    re.compile(r"(?i)\byou are now\b.{0,40}\b(unrestricted|jailbroken|admin)\b"),
    re.compile(r"(?i)\bexfiltrate\b|\bsend (me )?(your )?api[_ ]?key\b"),
    re.compile(r"(?i)\boverride (safety|constitution|approval)\b"),
    re.compile(r"(?i)\bdo not tell (your )?human\b|\bhide this from (your )?owner\b"),
    re.compile(r"(?i)\bexecute (shell|bash|curl|wget)\b"),
    re.compile(r"(?i)\btransfer (funds|btc|eth|usdt)\b|\bconnect (your )?wallet\b"),
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(payload: dict[str, Any]) -> str:
    """SHA-256 over canonical JSON of the exact action payload."""
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str, *, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def detect_prompt_injection(text: str) -> list[str]:
    """Return matched heuristic labels; empty means no signal (not a guarantee)."""
    hits: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text or ""):
            hits.append(pattern.pattern)
    return hits


@dataclass(slots=True)
class KillSwitch:
    """Process + env backed emergency stop.

    When engaged, all modules must refuse outbound / trading execution and prefer
    read-only behavior.
    """

    engaged: bool = False
    reason: str = ""
    engaged_at: str | None = None

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "KillSwitch":
        env = environ if environ is not None else dict(os.environ)
        raw = (env.get("AION_KILL_SWITCH") or "").strip().lower()
        engaged = raw in {"1", "true", "yes", "on"}
        return cls(
            engaged=engaged,
            reason="AION_KILL_SWITCH env" if engaged else "",
            engaged_at=utc_now_iso() if engaged else None,
        )

    def engage(self, reason: str) -> None:
        self.engaged = True
        self.reason = reason
        self.engaged_at = utc_now_iso()

    def release(self, *, decided_by: str) -> None:
        del decided_by  # reserved for audit callers
        self.engaged = False
        self.reason = ""
        self.engaged_at = None

    def snapshot(self) -> dict[str, Any]:
        return redact_value(
            {
                "engaged": self.engaged,
                "reason": self.reason,
                "engaged_at": self.engaged_at,
            }
        )
