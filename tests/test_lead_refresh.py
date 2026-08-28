from __future__ import annotations

from aion.moltbook.store import Phase2Store


def _row(*, lead_id: str, confidence: float, status: str = "pending_owner_review") -> dict:
    return {
        "lead_id": lead_id,
        "source_url": "https://www.moltbook.com/post/example",
        "requester_identity": "example",
        "stated_problem": "Need help fixing my deployment",
        "relevant_service": "Hosting and launch help",
        "fit_score": confidence,
        "confidence_score": confidence,
        "suggested_response": "draft",
        "risks": f"score={confidence}",
        "approval_status": status,
        "conversion_outcome": "uncontacted",
        "revenue_attributed": 0.0,
        "raw_excerpt": "example",
        "created_at": "2026-08-28T00:00:00+00:00",
        "content_hash": "same-content",
    }


def test_unreviewed_duplicate_is_refreshed(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    store = Phase2Store(str(tmp_path / "phase2.db"))
    store.upsert_lead(_row(lead_id="lead-1", confidence=0.85))
    store.upsert_lead(_row(lead_id="lead-2", confidence=0.42))
    row = store.list_leads()[0]
    assert row["lead_id"] == "lead-1"
    assert row["confidence_score"] == 0.42
    assert row["risks"] == "score=0.42"
    store.close()


def test_reviewed_duplicate_is_not_overwritten(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AION_DATABASE_URL", raising=False)
    store = Phase2Store(str(tmp_path / "phase2.db"))
    store.upsert_lead(_row(lead_id="lead-1", confidence=0.85, status="strong_lead"))
    store.upsert_lead(_row(lead_id="lead-2", confidence=0.42))
    row = store.list_leads()[0]
    assert row["lead_id"] == "lead-1"
    assert row["confidence_score"] == 0.85
    assert row["approval_status"] == "strong_lead"
    store.close()
