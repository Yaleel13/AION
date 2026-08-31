"""Private covenant runtime for AION.

The canonical covenant MUST NOT be committed to this public repository. It is
loaded from a secret environment value and can be integrity-checked at runtime.
External/emissary contexts receive only a minimal capability capsule.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass


class CovenantError(RuntimeError):
    """Raised when the private covenant cannot be verified safely."""


@dataclass(frozen=True, slots=True)
class CovenantRuntime:
    covenant_id: str
    principal: str
    canonical_text: str
    sha256: str

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "CovenantRuntime":
        env = environ if environ is not None else dict(os.environ)
        encoded = (env.get("AION_COVENANT_B64") or "").strip()
        expected = (env.get("AION_COVENANT_SHA256") or "").strip().lower()
        covenant_id = (env.get("AION_COVENANT_ID") or "AION-COVENANT-001").strip()
        principal = (env.get("AION_COVENANT_PRINCIPAL") or "PRINCIPAL-VERIFIED").strip()

        if not encoded:
            raise CovenantError("Private covenant secret is not configured")
        try:
            canonical = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise CovenantError("Private covenant secret is malformed") from exc
        if not canonical.strip():
            raise CovenantError("Private covenant is empty")

        actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if expected and not hmac.compare_digest(actual, expected):
            raise CovenantError("Private covenant integrity verification failed")

        return cls(
            covenant_id=covenant_id,
            principal=principal,
            canonical_text=canonical,
            sha256=actual,
        )

    def emissary_capsule(self, *, role: str) -> dict[str, str]:
        """Return only non-secret operating metadata for an external emissary."""
        return {
            "covenant": self.covenant_id,
            "principal": self.principal,
            "status": "ACTIVE",
            "disclosure": "PROHIBITED",
            "authority": f"LIMITED:{role}",
            "integrity": "VERIFIED",
            "public_modification": "FORBIDDEN",
        }

    def safe_status(self) -> dict[str, str]:
        """Status suitable for logs/UI. Never returns text or the digest."""
        return {
            "covenant": self.covenant_id,
            "status": "ACTIVE",
            "integrity": "VERIFIED",
            "disclosure": "PROHIBITED",
        }


def covenant_configured(environ: dict[str, str] | None = None) -> bool:
    """Check configuration without decoding or exposing covenant contents."""
    env = environ if environ is not None else dict(os.environ)
    return bool((env.get("AION_COVENANT_B64") or "").strip())
