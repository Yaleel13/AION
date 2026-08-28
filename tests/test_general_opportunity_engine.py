from __future__ import annotations

from aion.moltbook.leads import _buyer_signal, _match_service, _need_signal


def test_paid_gig_is_detected_as_explicit_revenue_opportunity() -> None:
    text = "Looking to hire a developer for a paid project. Budget is $1500 and I need help automating our workflow."
    service, track, fit = _match_service(text)
    assert service is not None
    assert track in {"paid_gig", "yalitek_service"}
    assert fit >= 0.65
    assert _buyer_signal(text) is True
    assert _need_signal(text) == "explicit"


def test_web3_bounty_is_detected_as_paid_work_not_live_trading() -> None:
    text = "Open web3 bounty for a smart contract developer. Paid in USDC after reviewed deliverables."
    service, track, fit = _match_service(text)
    assert service == "Web3 or crypto paid work"
    assert track == "crypto_work"
    assert fit >= 0.65
    assert _buyer_signal(text) is True
    assert _need_signal(text) == "explicit"


def test_crypto_market_chatter_is_not_a_revenue_lead() -> None:
    text = "Bitcoin looks bullish today and I think ETH could rally next week. Which token should I buy?"
    service, track, fit = _match_service(text)
    assert service is None
    assert track is None
    assert fit == 0.0
    assert _buyer_signal(text) is False
    assert _need_signal(text) is None


def test_grant_or_bounty_with_reward_intent_is_explicit() -> None:
    text = "Grant funding available for AI automation prototypes. Prize pool and paid challenge details are public."
    service, track, fit = _match_service(text)
    assert service == "Bounty or grant"
    assert track == "bounty_grant"
    assert fit >= 0.65
    assert _buyer_signal(text) is True
