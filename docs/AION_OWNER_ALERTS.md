# AION Owner Authentication & Alerts

**Status:** Implemented (code); email delivery blocked until Resend credentials verified  
**PR:** C

## Owner token

```bash
python3 scripts/generate_owner_token.py
# prints fingerprint only — never the raw token
```

- Env name: `AION_OWNER_TOKEN` (server-side only; never `NEXT_PUBLIC_`)
- Also refreshes placeholder `AION_APPROVAL_TOKEN_PEPPER` when needed
- FastAPI `/owner/*` already requires Bearer match

## Lead alerts (owner only)

`ControlledAutonomyEngine.alert_owner_lead` now:

1. Persists `lead_alerts` + audit
2. Attempts Resend email to **owner only**
3. Never contacts the prospective customer

Required email fields:

- Source URL
- Stated need
- Fit score
- Recommended YaliTek service
- Proposed public response
- Required owner decision
- Security or credibility concerns

## Secrets (names only)

| Name | Purpose |
|------|---------|
| `AION_OWNER_TOKEN` | Owner API bearer |
| `AION_APPROVAL_TOKEN_PEPPER` | Approval token hashing |
| `RESEND_API_KEY` | Transactional email |
| `AION_OWNER_ALERT_EMAIL` | Owner inbox |
| `AION_ALERT_FROM_EMAIL` | Verified Resend from address |
| `AION_OWNER_ALERTS_ENABLED` | `true`/`false` |

## Cost

Resend free tier typically covers low-volume owner alerts (**$0** until paid quota).  
Current Resend MCP/API key in this environment: **invalid** — owner must create/rotate a key and verify a sending domain (e.g. `yalitekonline.com`).

## Test results

- Unit tests mock Resend HTTP (pass)
- Live send: **blocked** until `RESEND_API_KEY` + verified `from` domain are provided

## Threat assessment

| Threat | Mitigation |
|--------|------------|
| Token in git/browser | `.env` gitignored; no NEXT_PUBLIC_; generator does not print token |
| Emailing prospects | Hard-coded owner `to[]` only |
| Secret in email body | Refuse send if body contains token/API key |
| Log leakage | Audit stores redacted detail; fingerprint only |

## Rollback

Set `AION_OWNER_ALERTS_ENABLED=false` or unset `RESEND_API_KEY`. Lead rows still persist in DB.
