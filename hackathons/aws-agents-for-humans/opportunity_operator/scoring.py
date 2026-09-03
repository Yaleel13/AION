from __future__ import annotations

from .models import DecisionPacket, Opportunity


REJECT_REASONS = {
    "requires_upfront_payment": "Requires upfront payment to qualify",
    "requires_wallet_connection_to_qualify": "Requires wallet connection to qualify",
    "is_speculative_trading": "Depends on speculative trading",
    "is_gambling": "Gambling-related opportunity",
    "is_expired": "Opportunity is expired",
    "unverifiable_payment_claim": "Payment claim is not independently verifiable",
}


def evaluate_opportunity(opportunity: Opportunity) -> DecisionPacket:
    reject_reasons = [
        reason for field, reason in REJECT_REASONS.items() if getattr(opportunity, field)
    ]
    if not any(item.official for item in opportunity.evidence):
        reject_reasons.append("No official source has been verified")

    if reject_reasons:
        return DecisionPacket(
            title=opportunity.title,
            score=0.0,
            decision="reject",
            reasons=reject_reasons,
            risks=reject_reasons,
            evidence_urls=[str(item.source_url) for item in opportunity.evidence],
            recommended_next_action="Do not pursue unless the disqualifying condition is resolved.",
        )

    normalized_value = min(opportunity.payout_value_usd / 5000.0, 10.0)
    effort_efficiency = min(10.0, 20.0 / max(opportunity.effort_hours, 1.0))
    score = (
        normalized_value * 0.25
        + opportunity.credibility_score * 0.20
        + opportunity.fit_score * 0.20
        + opportunity.urgency_score * 0.15
        + opportunity.eligibility_score * 0.15
        + effort_efficiency * 0.05
    )

    decision = "review" if score >= 6.0 else "deprioritize"
    reasons = [
        f"expected value=${opportunity.payout_value_usd:,.0f}",
        f"credibility={opportunity.credibility_score}/10",
        f"fit={opportunity.fit_score}/10",
        f"urgency={opportunity.urgency_score}/10",
        f"eligibility={opportunity.eligibility_score}/10",
    ]
    risks: list[str] = []
    if opportunity.credibility_score < 7:
        risks.append("Credibility requires additional diligence")
    if opportunity.eligibility_score < 7:
        risks.append("Eligibility is uncertain or conditional")
    if opportunity.effort_hours > 40:
        risks.append("High estimated effort")

    return DecisionPacket(
        title=opportunity.title,
        score=round(score, 2),
        decision=decision,
        reasons=reasons,
        risks=risks,
        evidence_urls=[str(item.source_url) for item in opportunity.evidence],
        recommended_next_action=(
            "Prepare a human-reviewed action packet."
            if decision == "review"
            else "Keep in the background queue unless conditions improve."
        ),
    )
