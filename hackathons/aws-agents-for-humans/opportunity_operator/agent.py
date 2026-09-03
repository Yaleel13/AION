from __future__ import annotations

from strands import Agent, tool

from .models import Opportunity
from .scoring import evaluate_opportunity


@tool
def evaluate_candidate(opportunity: dict) -> dict:
    """Evaluate one opportunity using deterministic safety and ranking rules."""
    parsed = Opportunity.model_validate(opportunity)
    return evaluate_opportunity(parsed).model_dump(mode="json")


SYSTEM_PROMPT = """
You are Opportunity Operator, a professional background agent built for the AWS
Agents for Humans hackathon.

Your task is to turn noisy opportunity information into a small, trustworthy,
human-review queue.

Operating rules:
1. Prefer official sources and independently verified evidence.
2. Treat Reddit and social posts as discovery leads only until an official source
   confirms the opportunity.
3. Reject anything requiring upfront payment to qualify, wallet connection merely
   to enter, speculative trading, gambling, unverifiable payment claims, or stale
   opportunities.
4. Rank legitimate opportunities by expected value, effort, urgency, eligibility,
   credibility, and technical fit.
5. Use evaluate_candidate for the final deterministic decision packet.
6. Never submit an application, contact a third party, move funds, connect a
   wallet, buy tokens, or perform another consequential external action.
7. Clearly distinguish verified facts, inference, recommendation, and uncertainty.
8. Surface only opportunities that warrant human review; otherwise stay concise.
""".strip()


agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[evaluate_candidate],
)


def run_operator(message: str) -> str:
    """Run a single Opportunity Operator turn."""
    result = agent(message)
    return str(result)
