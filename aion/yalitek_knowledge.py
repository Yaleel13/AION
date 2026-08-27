"""Load owner-approved YaliTek canonical knowledge (public-safe only).

Until ``AION_YALITEK_KNOWLEDGE_APPROVED=true``, this module returns inactive
status and must not be treated as pricing authority.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CANONICAL_DOC = (
    Path(__file__).resolve().parents[1] / "docs" / "YALITEK_CANONICAL_KNOWLEDGE.md"
)

# Paths that may be ingested from a future read-only YaliTek repo (allowlist).
APPROVED_DOC_GLOBS = (
    "docs/**/*.md",
    "README.md",
    "public/**/*.md",
)

FORBIDDEN_PATH_HINTS = (
    ".env",
    "credential",
    "secret",
    "customer",
    "private",
    "wallet",
    "keystore",
)


@dataclass(slots=True)
class YaliTekKnowledgeStatus:
    approved: bool
    document_path: str
    document_version: str | None
    github_repo_configured: str | None
    services: list[str]


def knowledge_approved(environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else dict(os.environ)
    return (env.get("AION_YALITEK_KNOWLEDGE_APPROVED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _parse_version(text: str) -> str | None:
    m = re.search(r"\*\*Version:\*\*\s*([^\n]+)", text)
    return m.group(1).strip() if m else None


def _parse_services(text: str) -> list[str]:
    services: list[str] = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = cells[0]
        if name in {"Service", "Field", "Link", "Check", "Legal / trade names"}:
            continue
        if name.startswith("---"):
            continue
        # Service catalog rows have a public description column.
        if len(cells) >= 3 and cells[1] and "Owner approval" in cells[2] or len(cells) >= 3:
            if name and name[0].isupper() and "http" not in name.lower():
                if name not in {"Business names and URLs confirmed"}:
                    services.append(name)
    # Dedupe while preserving order; filter noise
    out: list[str] = []
    noise = {
        "Value",
        "Public description",
        "Public price",
        "Notes",
        "Result",
        "Primary contact channel",
        "Owner alert inbox (ops)",
        "Website",
    }
    for s in services:
        if s in noise or s in out:
            continue
        if len(s) > 60:
            continue
        out.append(s)
    return out


def load_status(environ: dict[str, str] | None = None) -> YaliTekKnowledgeStatus:
    env = environ if environ is not None else dict(os.environ)
    approved = knowledge_approved(env)
    version = None
    services: list[str] = []
    if CANONICAL_DOC.is_file():
        text = CANONICAL_DOC.read_text(encoding="utf-8")
        version = _parse_version(text)
        if approved:
            services = _parse_services(text)
    return YaliTekKnowledgeStatus(
        approved=approved,
        document_path=str(CANONICAL_DOC),
        document_version=version,
        github_repo_configured=(env.get("AION_YALITEK_GITHUB_REPO") or "").strip() or None,
        services=services,
    )


def path_allowed_for_ingest(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    if any(h in lowered for h in FORBIDDEN_PATH_HINTS):
        return False
    name = Path(lowered).name
    if name.endswith((".pem", ".key", ".p12", ".env")):
        return False
    # Allowlist by suffix for docs only
    return name.endswith(".md") or name == "readme.md"


def public_safe_summary(environ: dict[str, str] | None = None) -> dict[str, Any]:
    status = load_status(environ)
    return {
        "approved": status.approved,
        "document_version": status.document_version,
        "github_repo_configured": status.github_repo_configured,
        "services": status.services if status.approved else [],
        "reliance": (
            "authoritative_for_public_recommendations"
            if status.approved
            else "draft_only_awaiting_owner_approval"
        ),
        "may_quote_unpublished_prices": False,
        "may_accept_work": False,
        "may_negotiate": False,
    }
