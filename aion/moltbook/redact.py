"""Redaction helpers for audit logs and error messages."""

from __future__ import annotations

import re
from typing import Any

# Patterns that may appear in payloads, URLs, or error bodies.
_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)(\S+)"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\s,\"']+)"),
    re.compile(r"(?i)\b(moltbook_(?:sk_)?[a-z0-9_-]{8,})\b"),
    re.compile(r"(?i)(bearer\s+)([a-z0-9_\-.]{8,})"),
]

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "token",
        "access_token",
        "refresh_token",
        "password",
        "secret",
        "verification_code",
        "claim_url",
        "email",
        "phone",
        "owner_email",
    }
)


def redact_text(value: str) -> str:
    """Redact credentials and common PII from free-form text."""
    out = value
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(lambda m: f"{m.group(1)}{REDACTED}", out)
    out = _EMAIL_RE.sub(REDACTED, out)
    out = _PHONE_RE.sub(REDACTED, out)
    return out


def redact_value(value: Any) -> Any:
    """Recursively redact sensitive structures for logging."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_value(item)
        return redacted
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
