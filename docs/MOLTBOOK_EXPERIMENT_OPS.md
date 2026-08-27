# Moltbook Experiment Operations — Remaining Phases

**Status:** Active for the 14-day controlled-growth experiment  
**Depends on:** Phase 1 read-only, Phase 2 foundation, controlled-autonomy activation

## Phase map

| Phase | Purpose | Status |
|-------|---------|--------|
| 1 | Read-only Moltbook client | Done |
| 2 | Drafts / approvals / leads / paper trading foundation | Done |
| Controlled autonomy activation | Guardrails + live arm | Done |
| **Experiment ops (this doc)** | Recurring cycle while quotas bind | **Execute now** |

## Experiment ops cycle

Run:

```bash
python3 scripts/experiment_ops_cycle.py --flush-queue --publish-next-draft
```

Each cycle:

1. **Drafts** — seed the 14-day campaign if empty (never auto-publishes without quota + flags)
2. **Paper trading** — one virtual BTC/ETH rebalance/mark tick
3. **Leads** — scan public feed; customize YaliTek response drafts; alert owner at confidence ≥ 0.7
4. **Daily report** — posts/comments/follows, blocks, leads, recommendations
5. **Queue flush** — publish queued comments only when comment quota allows (`--flush-queue`)
6. **Next draft** — publish the next campaign draft only when post quota allows (`--publish-next-draft`)

## Quota-bound holds

Outbound Moltbook writes still obey:

- ≤ 1 post / rolling 24h
- ≤ 3 comments / rolling 24h
- ≤ 5 follows / rolling 7d

When caps are full, the cycle stays read/prepare-only and keeps the next draft + queued reply ready
(with refreshed `seconds_remaining`). Re-run the same command after slots free.

## Still requires owner approval

- DMs / off-platform moves
- Pricing, discounts, proposals, contracts, delivery commitments
- Accepting work / requesting customer access
- Spending money / live crypto / wallets / exchanges
- Raising quotas or expanding permissions

## Owner dashboard

- UI: `http://127.0.0.1:3000/owner`
- FastAPI: `AION_API_BASE` (default `http://127.0.0.1:8000`) with `AION_OWNER_TOKEN`

## Crypto boundary

Paper trading only for ≥ 30 days before any live proposal. No trading keys.
