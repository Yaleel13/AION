import importlib.util
from pathlib import Path


def _load_score():
    path = Path(__file__).resolve().parent / "opportunity_navigator" / "scoring.py"
    spec = importlib.util.spec_from_file_location("opportunity_scoring", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.score_opportunity


def test_high_quality_opportunity_is_reviewed():
    score_opportunity = _load_score()
    result = score_opportunity(
        title="Verified AI hackathon",
        payout_value=10000,
        effort_hours=12,
        credibility=10,
        fit=9,
        urgency=8,
        eligibility=9,
    )
    assert result["decision"] == "review"
    assert result["score"] >= 6.0


def test_low_value_low_fit_opportunity_is_deprioritized():
    score_opportunity = _load_score()
    result = score_opportunity(
        title="Weak fit",
        payout_value=50,
        effort_hours=40,
        credibility=3,
        fit=2,
        urgency=2,
        eligibility=4,
    )
    assert result["decision"] == "deprioritize"
