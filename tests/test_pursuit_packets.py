from aion.pursuit_packets import build_pursuit_packet, build_top_packets


def _row(**overrides):
    row = {
        "opportunity_id": "opp-1",
        "source": "https://example.com/opportunity",
        "customer_problem": "Need website automation support",
        "proposed_solution": "Website and workflow automation",
        "estimated_revenue": 2500.0,
        "estimated_cost": 0.0,
        "expected_value": 1000.0,
        "capital_required": 0.0,
        "time_hours": 4.0,
        "major_risks": "verify terms",
        "ethical_considerations": "truthful claims only",
        "next_action": "verify scope",
        "authorization_required": "owner_before_transaction",
        "probability": 0.4,
        "confidence": 0.8,
    }
    row.update(overrides)
    return row


def test_commercial_packet_is_draft_only():
    packet = build_pursuit_packet(_row())
    assert packet.send_or_submit_enabled is False
    assert packet.approval_required == "owner_before_transaction"
    assert "NOT SENT" in packet.draft_material
    assert packet.economics["estimated_revenue"] == 2500.0


def test_grant_packet_never_claims_submission():
    packet = build_pursuit_packet(_row(
        customer_problem="Grant opportunity: technology assistance",
        authorization_required="owner_before_application",
        estimated_revenue=0.0,
        expected_value=0.0,
    ))
    assert "NOT SUBMITTED" in packet.draft_material
    assert packet.send_or_submit_enabled is False
    assert "commercial value/revenue" in packet.missing_information


def test_bid_packet_requires_owner_gate():
    packet = build_pursuit_packet(_row(
        customer_problem="Federal contract opportunity: website modernization",
        source="https://sam.gov/opportunities/123",
        authorization_required="owner_before_bid",
    ))
    assert packet.approval_required == "owner_before_bid"
    assert "BID PREPARATION DRAFT" in packet.draft_material
    assert "owner approval" in packet.draft_material.lower()


def test_do_not_pursue_filtered_from_top_packets():
    bad = _row(
        opportunity_id="bad",
        customer_problem="Unrelated agricultural equipment",
        proposed_solution="unknown",
        estimated_revenue=1000.0,
        expected_value=500.0,
    )
    good = _row(opportunity_id="good")
    packets = build_top_packets([bad, good], limit=2)
    assert all(packet["recommendation"] != "do_not_pursue" for packet in packets)
    assert any(packet["opportunity_id"] == "good" for packet in packets)
