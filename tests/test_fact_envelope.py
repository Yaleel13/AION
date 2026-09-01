"""Tests for FactEnvelope provenance helpers."""

from __future__ import annotations

from aion.fact_envelope import TruthClass, demo_fact, live_verified_fact


def test_demo_fact_is_explicitly_labeled() -> None:
    envelope = demo_fact({"message": "CI failed"}, source_object_id="signal:github")
    assert envelope.truth_class is TruthClass.DEMO
    assert envelope.is_demo is True
    assert envelope.confidence == 0.0
    assert envelope.source == "demo_fixture"
    assert envelope.value == {"message": "CI failed"}


def test_live_verified_fact_is_not_demo() -> None:
    envelope = live_verified_fact(
        {"backend": "postgres"},
        source="runtime_status",
        source_object_id="storage",
    )
    assert envelope.truth_class is TruthClass.LIVE_VERIFIED
    assert envelope.is_demo is False
    assert envelope.confidence == 1.0
    assert envelope.fetched_at is not None
