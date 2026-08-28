from google.adk.agents import Agent


def score_opportunity(
    title: str,
    payout_value: float,
    effort_hours: float,
    credibility: int,
    fit: int,
    urgency: int,
    eligibility: int,
) -> dict[str, object]:
    """Score a legitimate technical opportunity without taking financial action.

    credibility, fit, urgency, and eligibility are 0-10 integers supplied by the
    agent after reviewing the opportunity evidence. payout_value is the expected
    USD-equivalent value, not a token-price prediction.
    """
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


root_agent = Agent(
    name="opportunity_navigator",
    model="gemini-3.7-flash",
    description=(
        "A safe opportunity-ranking agent for legitimate AI, developer, grant, "
        "bounty, contract, partnership, and Web3 work."
    ),
    instruction="""
You are Opportunity Navigator, a new hackathon agent inspired by AION's
opportunity-discovery concept.

Your job is to evaluate legitimate ways a technical builder can create or earn
value. Rank opportunities using expected payout/value, effort, deadline urgency,
eligibility, credibility, and technical fit.

Safety rules:
- Never speculate on token prices or recommend gambling.
- Never ask the user to connect a wallet, send funds, buy tokens, or pay an
  upfront fee to qualify for work.
- Treat social posts and Reddit as discovery leads only until independently
  verified by an official source.
- Prefer grants, hackathons, funded bounties, paid open-source issues, freelance
  or contract work, partnerships/referrals, and legitimate Web3 developer work.
- Clearly distinguish verified facts from inference.
- Do not contact third parties or submit applications automatically.
- Use score_opportunity when enough evidence exists to compare an opportunity.

When returning results, keep the explanation concise and identify the evidence
still required before the opportunity should be pursued.
""".strip(),
    tools=[score_opportunity],
)
