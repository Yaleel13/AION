from __future__ import annotations

from aion.moltbook.leads import _buyer_signal, _confidence_band, _looks_informational, _need_signal


def test_direct_help_request_is_explicit_buyer_intent() -> None:
    text = "I need help with an n8n workflow that keeps failing in production."
    assert _buyer_signal(text) is True
    assert _need_signal(text) == "explicit"


def test_looking_to_hire_developer_is_explicit_buyer_intent() -> None:
    text = "Looking to hire a developer to fix our website deployment issue."
    assert _buyer_signal(text) is True
    assert _need_signal(text) == "explicit"


def test_community_insights_are_not_direct_buyer_intent() -> None:
    text = "How do you structure your heartbeat routines? Looking for community insights on Zapier and n8n."
    assert _buyer_signal(text) is False
    assert _need_signal(text) == "possible"


def test_troubleshooting_guide_is_informational() -> None:
    text = "MemOS Troubleshooting Guide: based on support requests from 100+ deployments, here's a comprehensive troubleshooting guide."
    assert _looks_informational(text) is True
    assert _buyer_signal(text) is False


def test_rules_and_templates_post_is_informational() -> None:
    text = "Welcome to Vibe Code — How to Post (Rules + Templates). Tools used: Zapier, n8n, Cursor."
    assert _looks_informational(text) is True
    assert _buyer_signal(text) is False


def test_possible_intent_cannot_reach_high_confidence_after_penalty() -> None:
    fit = 1.0
    possible_confidence = fit * 0.65
    assert _confidence_band(possible_confidence) == "worth_reviewing"
