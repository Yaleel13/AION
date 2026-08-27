# AION Durable Scheduler

**Status:** Implemented (GitHub Actions hourly + in-DB lock)  
**Depends on:** PR A durable storage

## Frequency

- **Cron:** `17 * * * *` (hourly) via `.github/workflows/aion-experiment-ops.yml`
- **Manual:** `workflow_dispatch` with optional flush/publish flags
- **Local:** `python3 scripts/experiment_ops_cycle.py --flush-queue --publish-next-draft`

## Guarantees

| Requirement | Mechanism |
|-------------|-----------|
| No overlapping executions | `scheduler_locks` row + Actions `concurrency` group |
| Distributed locking | SQLite/Postgres-ready `SchedulerStore.try_acquire_lock` |
| Transient retry | Existing Moltbook client retries; cycle records failure |
| Idempotency | Existing autonomy idempotency keys / content hashes |
| Rolling quotas | Unchanged autonomy counters |
| Read-only after repeated failures | `force_readonly` after 3 consecutive failures |
| Missed-cycle health alert | Alert if no success for 150 minutes |
| Kill switch | Checked before lock work; cycle short-circuits |
| No catch-up batches | Scheduler forces single cycle; `allow_catch_up=False` |

## Health

- State: `scheduler_state.last_success_at`, `consecutive_failures`, `cycle_history`
- Alerts: `health_alerts` table (email delivery in PR C)
- Summary file: `$AION_DATA_DIR/scheduler/last_cycle.json`

## Cost

GitHub Actions on a **public** repository: **$0** for the workflow itself.  
**Durable backend required:** managed Postgres ~**$10/mo** (see PR A) — workflow exits until `AION_DATABASE_URL` secret exists.  
Alternatively run the same script on any persistent host with `AION_DATA_DIR` (no GHA).


## Secrets required (names only, Actions repo secrets)

- `MOLTBOOK_API_KEY`
- `MOLTBOOK_EXPERIMENT_STARTED_AT` (optional if in DB risk_state)
- Optional overrides: `MOLTBOOK_*`, `AION_KILL_SWITCH`

## Rollback

1. Disable workflow (GitHub Actions → aion-experiment-ops → Disable).
2. Or set secret `AION_KILL_SWITCH=true`.
3. Clear force readonly: owner API / `ExperimentOpsScheduler.clear_force_readonly()`.

## Threat assessment

| Threat | Mitigation |
|--------|------------|
| Double publish after downtime | No catch-up; quotas + idempotency |
| Secret leakage in logs | Workflow never echoes secrets; redaction in audit |
| Cache loss on Actions | Prefer managed Postgres after $10/mo approval; cache is best-effort |
| Stuck lock | TTL expiry (default 900s) |
