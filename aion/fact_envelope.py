"""Provenance metadata for integration-derived facts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TruthClass(str, Enum):
    LIVE_VERIFIED = "LIVE_VERIFIED"
    LIVE_STALE = "LIVE_STALE"
    INFERRED = "INFERRED"
    DEMO = "DEMO"


DEMO_FIXTURE_SOURCE = "demo_fixture"


class FactEnvelope(BaseModel):
    value: Any
    truth_class: TruthClass
    source: str
    source_object_id: str | None = None
    observed_at: datetime | None = None
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    sync_cursor: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_demo: bool = False
    trace_id: str | None = None


def demo_fact(
    value: Any,
    *,
    source: str = DEMO_FIXTURE_SOURCE,
    source_object_id: str | None = None,
) -> FactEnvelope:
    """Wrap fixture / synthetic data — never present as live provider telemetry."""
    return FactEnvelope(
        value=value,
        truth_class=TruthClass.DEMO,
        source=source,
        source_object_id=source_object_id,
        fetched_at=datetime.now(UTC),
        confidence=0.0,
        is_demo=True,
    )


def live_verified_fact(
    value: Any,
    *,
    source: str,
    source_object_id: str | None = None,
    observed_at: datetime | None = None,
    fetched_at: datetime | None = None,
    expires_at: datetime | None = None,
    sync_cursor: str | None = None,
    trace_id: str | None = None,
) -> FactEnvelope:
    """Wrap verified live provider or runtime data."""
    return FactEnvelope(
        value=value,
        truth_class=TruthClass.LIVE_VERIFIED,
        source=source,
        source_object_id=source_object_id,
        observed_at=observed_at,
        fetched_at=fetched_at or datetime.now(UTC),
        expires_at=expires_at,
        sync_cursor=sync_cursor,
        confidence=1.0,
        is_demo=False,
        trace_id=trace_id,
    )
