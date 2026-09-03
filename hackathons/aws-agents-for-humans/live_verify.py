from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from opportunity_operator.agent import run_operator
from opportunity_operator.bedrock import DEFAULT_MODEL_ID, DEFAULT_REGION


SAFE_PROMPT = """
Evaluate this hypothetical opportunity using your deterministic tool and return a
concise human-review recommendation. This is only a local verification fixture;
do not browse, submit forms, contact anyone, or perform external actions.

Opportunity:
- title: Verified AI automation contract
- type: freelance_contract
- summary: A verified buyer requests production AI automation work.
- payout_value_usd: 7500
- effort_hours: 40
- eligibility_score: 8
- credibility_score: 9
- fit_score: 10
- urgency_score: 8
- evidence: official sponsor/marketplace source supplied
- requires_upfront_payment: false
- requires_wallet_connection_to_qualify: false
- is_speculative_trading: false
- is_gambling: false
- is_expired: false
- unverifiable_payment_claim: false
""".strip()


def main() -> int:
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION))
    model_id = os.getenv("AION_AWS_MODEL_ID", DEFAULT_MODEL_ID)

    started = datetime.now(timezone.utc)
    print(json.dumps({
        "event": "live_verification_start",
        "timestamp": started.isoformat(),
        "provider": "amazon-bedrock",
        "framework": "strands-agents",
        "model_id": model_id,
        "region": region,
    }))

    try:
        output = run_operator(SAFE_PROMPT)
    except Exception as exc:
        print(json.dumps({
            "event": "live_verification_failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }))
        return 1

    print(json.dumps({
        "event": "live_verification_success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output": output,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
