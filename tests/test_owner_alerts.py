"""Owner alert payload + Resend send path (mocked HTTP)."""

from __future__ import annotations

import json

import httpx
import pytest

from aion.owner_alerts import (
    OwnerAlertConfig,
    OwnerAlertService,
    generate_owner_token,
    owner_token_fingerprint,
)


def test_token_fingerprint_stable_and_short():
    tok = generate_owner_token()
    fp = owner_token_fingerprint(tok)
    assert len(fp) == 12
    assert fp == owner_token_fingerprint(tok)
    assert fp != tok


def test_lead_alert_requires_fields():
    svc = OwnerAlertService(config=None)
    with pytest.raises(ValueError):
        svc.build_lead_alert_payload({"lead_id": "x"})


def test_lead_alert_payload_complete():
    svc = OwnerAlertService(config=None)
    payload = svc.build_lead_alert_payload(
        {
            "lead_id": "L1",
            "source_url": "https://example.com/p/1",
            "stated_problem": "Need website repair",
            "fit_score": 0.8,
            "confidence_score": 0.75,
            "relevant_service": "Website repair",
            "suggested_response": "Happy to help diagnose publicly.",
            "risks": "Unverified account",
        }
    )
    text = svc.format_lead_alert_text(payload)
    assert "Source URL" in text
    assert "Website repair" in text
    assert "Required owner decision" in text


def test_send_lead_alert_owner_only(monkeypatch):
    cfg = OwnerAlertConfig(
        resend_api_key="re_test_key",
        owner_email="owner@example.com",
        from_email="aion@example.com",
    )
    svc = OwnerAlertService(config=cfg)

    class FakeResp:
        status_code = 200
        content = b'{"id":"email_123"}'

        def json(self):
            return {"id": "email_123"}

    captured = {}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    result = svc.send_lead_alert(
        {
            "lead_id": "L1",
            "source_url": "https://example.com/p/1",
            "stated_problem": "Broken checkout",
            "fit_score": 0.9,
            "confidence_score": 0.8,
            "relevant_service": "Website repair",
            "suggested_response": "I can share a public diagnostic checklist.",
            "risks": "None",
        }
    )
    assert result["sent"] is True
    assert result["prospect_contacted"] is False
    assert captured["json"]["to"] == ["owner@example.com"]
    assert "re_test_key" not in json.dumps(captured["json"])


def test_refuses_body_containing_api_key(monkeypatch):
    cfg = OwnerAlertConfig(
        resend_api_key="re_secret_should_not_appear",
        owner_email="owner@example.com",
        from_email="aion@example.com",
    )
    svc = OwnerAlertService(config=cfg)
    with pytest.raises(RuntimeError):
        # Force _send with poisoned body
        svc._send(
            subject="x",
            text="leak re_secret_should_not_appear",
            idempotency_key="k",
            tag=("alert_type", "test"),
        )
