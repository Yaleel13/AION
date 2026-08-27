"""Owner authentication helpers and outbound owner-only alerts.

Never send secrets, tokens, or customer PII dumps to browsers, logs, git,
Moltbook, or model prompts. Lead alerts contact the OWNER only — never the
prospective customer.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Any

import httpx

from aion.moltbook.redact import redact_value
from aion.moltbook.security import utc_now_iso


REQUIRED_LEAD_ALERT_FIELDS = (
    "source_url",
    "stated_need",
    "fit_score",
    "recommended_service",
    "proposed_public_response",
    "required_owner_decision",
    "security_or_credibility_concerns",
)


def generate_owner_token(*, nbytes: int = 32) -> str:
    """Cryptographically strong bearer token for server-side owner API only."""
    return secrets.token_urlsafe(nbytes)


def owner_token_fingerprint(token: str) -> str:
    """Non-reversible fingerprint for logs (never log the raw token)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def ensure_owner_token_configured(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ if environ is not None else dict(os.environ)
    token = (env.get("AION_OWNER_TOKEN") or "").strip()
    if not token or token.startswith("your_"):
        return {"configured": False, "fingerprint": None}
    return {"configured": True, "fingerprint": owner_token_fingerprint(token)}


@dataclass(slots=True)
class OwnerAlertConfig:
    resend_api_key: str
    owner_email: str
    from_email: str
    enabled: bool = True

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> OwnerAlertConfig | None:
        env = environ if environ is not None else dict(os.environ)
        key = (env.get("RESEND_API_KEY") or "").strip()
        owner = (env.get("AION_OWNER_ALERT_EMAIL") or "").strip()
        from_email = (env.get("AION_ALERT_FROM_EMAIL") or "").strip()
        enabled = (env.get("AION_OWNER_ALERTS_ENABLED") or "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not key or not owner or not from_email:
            return None
        if key.startswith("your_"):
            return None
        return cls(
            resend_api_key=key,
            owner_email=owner,
            from_email=from_email,
            enabled=enabled,
        )


class OwnerAlertService:
    """Send owner-only emails via Resend. Never emails prospects."""

    def __init__(self, config: OwnerAlertConfig | None = None):
        self.config = config if config is not None else OwnerAlertConfig.from_env()

    @property
    def configured(self) -> bool:
        return self.config is not None and self.config.enabled

    def build_lead_alert_payload(self, lead: dict[str, Any]) -> dict[str, Any]:
        rules = lead.get("requires_owner_before") or [
            "move to email/other platform",
            "quote a price",
            "offer consultation",
            "request customer files/access",
            "accept work / delivery commitments",
        ]
        payload = {
            "lead_id": lead.get("lead_id"),
            "source_url": lead.get("source_url") or "",
            "stated_need": lead.get("stated_problem") or lead.get("stated_need") or "",
            "fit_score": lead.get("fit_score"),
            "confidence_score": lead.get("confidence_score"),
            "recommended_service": lead.get("relevant_service")
            or lead.get("recommended_service")
            or "",
            "proposed_public_response": lead.get("suggested_response")
            or lead.get("proposed_public_response")
            or "",
            "required_owner_decision": (
                "Approve or reject next steps. Do not contact the prospect until you decide. "
                f"Owner approval still required before: {', '.join(rules)}."
            ),
            "security_or_credibility_concerns": lead.get("risks")
            or lead.get("security_or_credibility_concerns")
            or "None flagged",
        }
        missing = [k for k in REQUIRED_LEAD_ALERT_FIELDS if not str(payload.get(k) or "").strip()]
        if missing:
            raise ValueError(f"lead alert missing fields: {missing}")
        return payload

    def format_lead_alert_text(self, payload: dict[str, Any]) -> str:
        return (
            "AION qualified-lead alert (owner only — do not forward to prospect)\n\n"
            f"Source URL: {payload['source_url']}\n"
            f"Stated need: {payload['stated_need']}\n"
            f"Fit score: {payload['fit_score']}\n"
            f"Confidence: {payload.get('confidence_score')}\n"
            f"Recommended YaliTek service: {payload['recommended_service']}\n\n"
            f"Proposed public response:\n{payload['proposed_public_response']}\n\n"
            f"Required owner decision:\n{payload['required_owner_decision']}\n\n"
            f"Security or credibility concerns:\n{payload['security_or_credibility_concerns']}\n"
        )

    def send_lead_alert(self, lead: dict[str, Any]) -> dict[str, Any]:
        payload = self.build_lead_alert_payload(lead)
        text = self.format_lead_alert_text(payload)
        subject = (
            f"[AION] Lead · {payload['recommended_service']} · "
            f"fit {payload['fit_score']}"
        )
        return self._send(
            subject=subject,
            text=text,
            idempotency_key=f"lead-{payload.get('lead_id')}",
            tag=("alert_type", "qualified_lead"),
        )

    def send_health_alert(self, alert_type: str, detail: dict[str, Any]) -> dict[str, Any]:
        safe = redact_value(detail)
        text = (
            f"AION health alert: {alert_type}\n\n"
            f"Detail (redacted):\n{safe}\n\n"
            "No catch-up publish batch will be attempted automatically.\n"
        )
        return self._send(
            subject=f"[AION] Health · {alert_type}",
            text=text,
            idempotency_key=f"health-{alert_type}-{safe.get('alert_id', utc_now_iso())}",
            tag=("alert_type", alert_type),
        )

    def _send(
        self,
        *,
        subject: str,
        text: str,
        idempotency_key: str,
        tag: tuple[str, str],
    ) -> dict[str, Any]:
        if not self.configured or self.config is None:
            return {
                "sent": False,
                "reason": "owner_alerts_not_configured",
                "configured": False,
            }
        # Defense: never include owner token or API key material in body.
        forbidden = (
            os.getenv("AION_OWNER_TOKEN") or "",
            self.config.resend_api_key,
        )
        for secret in forbidden:
            if secret and secret in text:
                raise RuntimeError("refusing to send alert that contains a secret value")

        headers = {
            "Authorization": f"Bearer {self.config.resend_api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key[:256],
        }
        body = {
            "from": self.config.from_email,
            "to": [self.config.owner_email],
            "subject": subject,
            "text": text,
            "tags": [{"name": tag[0], "value": tag[1]}],
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.resend.com/emails", headers=headers, json=body)
        if resp.status_code >= 400:
            return {
                "sent": False,
                "reason": "resend_error",
                "status_code": resp.status_code,
                # Do not include response body if it might echo config.
            }
        data = resp.json() if resp.content else {}
        return {
            "sent": True,
            "provider": "resend",
            "email_id": data.get("id"),
            "to_owner_only": True,
            "prospect_contacted": False,
        }
