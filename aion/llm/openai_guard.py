"""OpenAI provider guardrails: allowlist, cost ceilings, safe fallback.

Secrets, private repos, customer records, and founder private context must never
be sent to the model. Gemini is not configured in this module.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aion.moltbook.security import detect_prompt_injection, utc_now, utc_now_iso

DEFAULT_ALLOWLIST = (
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4.1",
    "o4-mini",
)

# Rough USD per 1M tokens (approximate; for ceiling enforcement only).
PRICE_PER_MTOK = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
}

SECRET_PATTERNS = [
    re.compile(r"(?i)sk-[a-z0-9]{10,}"),
    re.compile(r"(?i)ghs_[A-Za-z0-9_]{10,}"),
    re.compile(r"(?i)ghp_[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)BEGIN (RSA |OPENSSH )?PRIVATE KEY"),
    re.compile(r"(?i)AION_OWNER_TOKEN\s*="),
    re.compile(r"(?i)OPENAI_API_KEY\s*="),
    re.compile(r"(?i)MOLTBOOK_API_KEY\s*="),
]


@dataclass(slots=True)
class OpenAIGuardConfig:
    allowlist: tuple[str, ...]
    max_input_tokens: int
    max_output_tokens: int
    daily_cost_usd: float
    timeout_seconds: float
    max_retries: int
    default_model: str

    @classmethod
    def from_env(cls) -> OpenAIGuardConfig:
        raw = (os.getenv("AION_OPENAI_MODEL_ALLOWLIST") or "").strip()
        allow = tuple(x.strip() for x in raw.split(",") if x.strip()) or DEFAULT_ALLOWLIST
        default = os.getenv("AION_MODEL", "gpt-4o-mini")
        if default not in allow:
            default = allow[0]
        return cls(
            allowlist=allow,
            max_input_tokens=int(os.getenv("AION_OPENAI_MAX_INPUT_TOKENS", "4000")),
            max_output_tokens=int(os.getenv("AION_OPENAI_MAX_OUTPUT_TOKENS", "1200")),
            daily_cost_usd=float(os.getenv("AION_OPENAI_DAILY_COST_USD", "5.0")),
            timeout_seconds=float(os.getenv("AION_OPENAI_TIMEOUT_SECONDS", "45")),
            max_retries=int(os.getenv("AION_OPENAI_MAX_RETRIES", "2")),
            default_model=default,
        )


class OpenAIUsageStore:
    def __init__(self, path: str | None = None):
        if path is None:
            try:
                from aion.durable.paths import resolve_durable_paths

                path = str(resolve_durable_paths().root / "openai_usage.db")
            except Exception:
                path = "data/aion/openai_usage.db"
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              day TEXT NOT NULL,
              model TEXT NOT NULL,
              input_tokens INTEGER NOT NULL,
              output_tokens INTEGER NOT NULL,
              estimated_cost_usd REAL NOT NULL,
              success INTEGER NOT NULL,
              detail_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def record(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
        success: bool,
        detail: dict[str, Any],
    ) -> None:
        day = utc_now().date().isoformat()
        self._conn.execute(
            """
            INSERT INTO usage_events(
              timestamp, day, model, input_tokens, output_tokens,
              estimated_cost_usd, success, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                day,
                model,
                input_tokens,
                output_tokens,
                estimated_cost_usd,
                1 if success else 0,
                json.dumps(detail, default=str),
            ),
        )
        self._conn.commit()

    def spend_today_usd(self) -> float:
        day = utc_now().date().isoformat()
        row = self._conn.execute(
            "SELECT COALESCE(SUM(estimated_cost_usd),0) AS s FROM usage_events WHERE day=?",
            (day,),
        ).fetchone()
        return float(row["s"] if row else 0.0)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICE_PER_MTOK.get(model) or {"input": 2.0, "output": 8.0}
    return (input_tokens / 1_000_000.0) * prices["input"] + (
        output_tokens / 1_000_000.0
    ) * prices["output"]


def approx_token_count(text: str) -> int:
    # Cheap heuristic (~4 chars/token) — ceiling guard, not billing.
    return max(1, len(text) // 4)


def scrub_secrets(text: str) -> str:
    out = text
    for pat in SECRET_PATTERNS:
        out = pat.sub("[REDACTED_SECRET]", out)
    return out


def contains_forbidden_context(text: str) -> list[str]:
    reasons: list[str] = []
    lowered = text.lower()
    if "owner_private_context" in lowered or "private founder" in lowered:
        reasons.append("private_founder_context")
    if "customer record" in lowered or "customer pii" in lowered:
        reasons.append("customer_information")
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            reasons.append("secret_material")
            break
    inj = detect_prompt_injection(text)
    if inj:
        reasons.append("prompt_injection")
    return reasons


@dataclass(slots=True)
class GuardedRequest:
    model: str
    messages: list[dict[str, str]]
    max_output_tokens: int


@dataclass(slots=True)
class GuardedResult:
    ok: bool
    fallback: bool
    response: str
    model: str
    usage: dict[str, Any]
    reasons: list[str]


class OpenAIGuard:
    def __init__(
        self,
        config: OpenAIGuardConfig | None = None,
        usage: OpenAIUsageStore | None = None,
    ):
        self.config = config or OpenAIGuardConfig.from_env()
        self.usage = usage or OpenAIUsageStore()

    def validate_model(self, model: str) -> str:
        if model not in self.config.allowlist:
            raise ValueError(f"model_not_allowlisted:{model}")
        return model

    def prepare(
        self,
        *,
        message: str,
        system_prompt: str | None,
        model: str | None,
    ) -> GuardedRequest | GuardedResult:
        model_name = self.validate_model(model or self.config.default_model)
        spend = self.usage.spend_today_usd()
        if spend >= self.config.daily_cost_usd:
            return GuardedResult(
                ok=False,
                fallback=True,
                response=(
                    "AION is using non-LLM safe mode for the rest of today because the "
                    f"OpenAI daily cost ceiling (${self.config.daily_cost_usd:.2f}) was reached."
                ),
                model=model_name,
                usage={"daily_spend_usd": spend, "ceiling_usd": self.config.daily_cost_usd},
                reasons=["daily_cost_ceiling"],
            )

        raw_sys = system_prompt or ""
        raw_user = message or ""
        reasons = contains_forbidden_context(raw_sys) + contains_forbidden_context(raw_user)
        if reasons:
            return GuardedResult(
                ok=False,
                fallback=True,
                response=(
                    "Request blocked from the model by AION safety boundaries. "
                    "Safe non-LLM mode: rephrase without secrets, private context, "
                    "or injection instructions."
                ),
                model=model_name,
                usage={},
                reasons=sorted(set(reasons)),
            )

        sys = scrub_secrets(raw_sys)
        user = scrub_secrets(raw_user)

        # Truncate oversized input rather than sending unbounded prompts.
        max_chars = self.config.max_input_tokens * 4
        if len(user) > max_chars:
            user = user[:max_chars] + "\n[truncated_for_token_limit]"

        messages: list[dict[str, str]] = []
        if sys:
            messages.append({"role": "system", "content": sys})
        messages.append({"role": "user", "content": user})
        return GuardedRequest(
            model=model_name,
            messages=messages,
            max_output_tokens=self.config.max_output_tokens,
        )

    def record_usage(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        detail: dict[str, Any] | None = None,
    ) -> float:
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        self.usage.record(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            success=success,
            detail=detail or {},
        )
        return cost

    def validate_structured(self, text: str, *, schema_keys: list[str] | None = None) -> dict[str, Any]:
        """If output looks like JSON, validate keys; else wrap as plain text."""
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty_model_output")
        if stripped.startswith("{") and stripped.endswith("}"):
            data = json.loads(stripped)
            if schema_keys:
                missing = [k for k in schema_keys if k not in data]
                if missing:
                    raise ValueError(f"structured_output_missing:{missing}")
            return data
        return {"text": stripped}
