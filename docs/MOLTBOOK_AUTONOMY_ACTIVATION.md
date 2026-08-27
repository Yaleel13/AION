# Controlled Autonomy — Activation Record

**Status:** Pending merge of activation follow-up; production must start in dry-run.  
**Depends on:** Merged [#17](https://github.com/Yaleel13/AION/pull/17)  
**Follow-up PR:** [#18](https://github.com/Yaleel13/AION/pull/18)

## Required configuration sequence

1. Deploy / start with:
   - `MOLTBOOK_CONTROLLED_AUTONOMY=true`
   - `MOLTBOOK_AUTONOMY_DRY_RUN=true`
   - `AION_KILL_SWITCH=false`
2. Run `python3 scripts/controlled_autonomy_production_dry_run.py`
3. Only after every verification passes, set:
   - `MOLTBOOK_AUTONOMY_DRY_RUN=false`
   - `MOLTBOOK_EXPERIMENT_STARTED_AT=<ISO-UTC>`
4. Record the activation timestamp and begin the 14-day clock.

Private founder/owner charter remains in gitignored `identity/OWNER_PRIVATE_CONTEXT.md`
and must never be loaded into public agent instructions or endpoints.

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

## Owner dashboard access

- UI: `http://127.0.0.1:3000/owner` (Next.js) with FastAPI at `AION_API_BASE` (default `http://127.0.0.1:8000`)
- Requires server-side `AION_OWNER_TOKEN` (never `NEXT_PUBLIC_`)
- Direct API: `GET /owner/dashboard` with `Authorization: Bearer <AION_OWNER_TOKEN>`
