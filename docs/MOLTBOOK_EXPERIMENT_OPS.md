# Moltbook Experiment Operations — Remaining Phases

**Status:** Ready after controlled-autonomy is armed in the target environment.  
**Repository default:** Controlled autonomy is **inactive**; do not treat this doc as authorization to publish.

**Depends on:** Phase 1 read-only, Phase 2 foundation, and an explicit autonomy activation in the running environment (`MOLTBOOK_CONTROLLED_AUTONOMY=true`).

## Phase map

| Phase | Purpose | Status |
|-------|---------|--------|
| 1 | Read-only Moltbook client | Done |
| 2 | Drafts / approvals / leads / paper trading foundation | Done (execute off by default) |
| Controlled autonomy | Guardrails + optional live arm | Implemented; **inactive by default** |
| **Experiment ops (this doc)** | Recurring cycle while quotas bind | Run only when autonomy is active in-env |

## Experiment ops cycle

Run (only on an armed environment):

```bash
python3 scripts/experiment_ops_cycle.py --flush-queue --publish-next-draft
```

Each cycle:

1. **Drafts** — seed the 14-day campaign if empty (never auto-publishes without quota + flags)
2. **Paper trading** — one virtual BTC/ETH rebalance/mark tick
3. **Leads** — scan public feed; customize YaliTek response drafts; alert owner at confidence ≥ 0.7
4. **Daily report** — posts/comments/follows, blocks, leads, recommendations
5. **Queue flush** — publish queued comments only when comment quota allows (`--flush-queue`)
6. **Comment backlog** — after the primary queued reply, publish the next prioritized ready backlog comment if a slot remains
7. **Next draft** — publish the next campaign draft only when post quota allows (`--publish-next-draft`)

## Quota-bound holds

Outbound Moltbook writes still obey owner ceilings (not targets):

- ≤ 2 posts / rolling 24h (≥ 2h between posts) when expanded profile is active
- ≤ 8 comments / rolling 24h (≥ 10 min between; ≤ 2 / hour)
- ≤ 15 follows / rolling 7d (no rapid bursts)
- Auto-reduce profile: 1 / 3 / 5
- Platform rate limits always override

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
