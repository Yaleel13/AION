def score_opportunity(
    title: str,
    payout_value: float,
    effort_hours: float,
    credibility: int,
    fit: int,
    urgency: int,
    eligibility: int,
) -> dict[str, object]:
    """Score a legitimate technical opportunity without taking financial action."""
    safe_effort = max(effort_hours, 1.0)
    normalized_value = min(payout_value / 5000.0, 10.0)
    score = (
        normalized_value * 0.25
        + credibility * 0.20
        + fit * 0.20
        + urgency * 0.15
        + eligibility * 0.15
        + min(10.0 / safe_effort, 10.0) * 0.05
    )
    return {
        "title": title,
        "score": round(score, 2),
        "expected_value_usd": payout_value,
        "effort_hours": effort_hours,
        "decision": "review" if score >= 6.0 else "deprioritize",
    }
