# Controlled Autonomy — Activation Record

**Status:** LIVE-ARMED (14-day experiment clock started)  
**Merged PR:** [#17](https://github.com/Yaleel13/AION/pull/17) @ `6dfcb2a` (reviewed commit `f69a7d9`)  
**Activation timestamp (UTC):** `2026-08-27T09:43:24+00:00`  
**Ends (UTC):** `2026-09-10T09:43:24+00:00`

## Configuration state

| Variable | Value |
|----------|-------|
| `MOLTBOOK_CONTROLLED_AUTONOMY` | `true` |
| `MOLTBOOK_AUTONOMY_DRY_RUN` | `false` |
| `MOLTBOOK_EXPERIMENT_STARTED_AT` | `2026-08-27T09:43:24+00:00` |
| `AION_KILL_SWITCH` | `false` |

Private founder/owner charter is loaded from gitignored `identity/OWNER_PRIVATE_CONTEXT.md` only (public repo; never publish that text).

## Pre-live verification

Production dry-run + adversarial guardrail verification: **all passed** before `DRY_RUN=false`.

Dry-run cycle (no network publish): 1 post rehearsal, 1 comment rehearsal, 1 follow rehearsal, 1 lead alert, daily report generated.

## First scheduled action

- Type: `create_post` (next eligible original post under 1/24h)
- Must obey topic allowlist, denylists, secret/PII scan, and audit logging
- No DMs; no pricing/contracts/off-platform without owner approval

## Kill-switch procedure

1. Set `AION_KILL_SWITCH=true`, **or**
2. `POST /owner/kill-switch` with `{"engage": true, "reason": "..."}` + owner token, **or**
3. Owner dashboard → Engage kill switch  

Effect: all outbound refused; prefer read-only.

## Daily reporting schedule

- On demand / once per UTC day
- `POST /owner/autonomy/daily-report` or Owner dashboard button
- Includes actions+links, leads, blocks, limits/risk, recommended decisions

## Crypto boundary

Paper trading only. No wallets, exchanges, live trades, leverage, deposits, withdrawals, or token promotion.
