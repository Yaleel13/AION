from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


OpportunityType = Literal[
    "hackathon",
    "grant",
    "bounty",
    "open_source_paid_issue",
    "freelance_contract",
    "partnership_referral",
    "web3_paid_work",
]


class Evidence(BaseModel):
    source_url: HttpUrl
    source_name: str
    official: bool = False
    retrieved_at: datetime | None = None
    notes: str = ""


class Opportunity(BaseModel):
    title: str
    opportunity_type: OpportunityType
    summary: str
    payout_value_usd: float = Field(default=0, ge=0)
    effort_hours: float = Field(default=1, gt=0)
    deadline: datetime | None = None
    eligibility_score: int = Field(default=5, ge=0, le=10)
    credibility_score: int = Field(default=5, ge=0, le=10)
    fit_score: int = Field(default=5, ge=0, le=10)
    urgency_score: int = Field(default=5, ge=0, le=10)
    evidence: list[Evidence] = Field(default_factory=list)
    requires_upfront_payment: bool = False
    requires_wallet_connection_to_qualify: bool = False
    is_speculative_trading: bool = False
    is_gambling: bool = False
    is_expired: bool = False
    unverifiable_payment_claim: bool = False


class DecisionPacket(BaseModel):
    title: str
    score: float
    decision: Literal["review", "deprioritize", "reject"]
    reasons: list[str]
    risks: list[str]
    evidence_urls: list[str]
    recommended_next_action: str
    requires_human_approval: bool = True
