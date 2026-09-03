from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .models import Evidence, Opportunity


@dataclass(slots=True)
class SourceRecord:
    source_name: str
    source_url: str
    official: bool
    payload: dict[str, Any]


def parse_deadline(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_record(record: SourceRecord) -> Opportunity:
    data = record.payload
    return Opportunity(
        title=str(data["title"]),
        opportunity_type=data["opportunity_type"],
        summary=str(data.get("summary") or ""),
        payout_value_usd=float(data.get("payout_value_usd") or 0),
        effort_hours=float(data.get("effort_hours") or 1),
        deadline=parse_deadline(data.get("deadline")),
        eligibility_score=int(data.get("eligibility_score") or 5),
        credibility_score=int(data.get("credibility_score") or 5),
        fit_score=int(data.get("fit_score") or 5),
        urgency_score=int(data.get("urgency_score") or 5),
        requires_upfront_payment=bool(data.get("requires_upfront_payment", False)),
        requires_wallet_connection_to_qualify=bool(
            data.get("requires_wallet_connection_to_qualify", False)
        ),
        is_speculative_trading=bool(data.get("is_speculative_trading", False)),
        is_gambling=bool(data.get("is_gambling", False)),
        is_expired=bool(data.get("is_expired", False)),
        unverifiable_payment_claim=bool(data.get("unverifiable_payment_claim", False)),
        evidence=[
            Evidence(
                source_url=record.source_url,
                source_name=record.source_name,
                official=record.official,
                retrieved_at=datetime.now(timezone.utc),
            )
        ],
    )


class JsonFeedAdapter:
    """Read a controlled public JSON feed and normalize candidate records.

    The adapter performs retrieval only. It never follows instructions embedded in
    source content, never submits forms, and never sends credentials or funds.
    """

    def __init__(self, source_name: str, url: str, *, official: bool = False) -> None:
        self.source_name = source_name
        self.url = url
        self.official = official

    async def fetch(self, client: httpx.AsyncClient | None = None) -> list[Opportunity]:
        owns_client = client is None
        http = client or httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        try:
            response = await http.get(self.url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            rows = payload if isinstance(payload, list) else payload.get("items", [])
            opportunities: list[Opportunity] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                opportunities.append(
                    normalize_record(
                        SourceRecord(
                            source_name=self.source_name,
                            source_url=self.url,
                            official=self.official,
                            payload=row,
                        )
                    )
                )
            return opportunities
        finally:
            if owns_client:
                await http.aclose()
