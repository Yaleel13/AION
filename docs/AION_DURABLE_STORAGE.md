# AION Durable Storage

**Status:** Implemented (SQLite under `AION_DATA_DIR`; Postgres schema ready)  
**PR:** Durable database and migration

## Selected infrastructure

| Layer | Choice | Monthly cost | Notes |
|-------|--------|--------------|-------|
| Default durable files | SQLite under `AION_DATA_DIR` (default `data/aion/`) | **$0** | Survives process restart if the volume is persistent |
| Managed Postgres (optional) | Dedicated Supabase project `aion-ops`, schema `aion` | **$10/mo** (org quote) | **Not provisioned** until owner confirms expense |
| Forbidden | YaliTekonline / Elaria Supabase projects | — | AION must not touch those tables |

Least privilege: when Postgres is approved, create a role limited to schema `aion` only.

## Environment

```bash
AION_DATA_DIR=data/aion          # durable root (gitignored)
# Optional overrides (still under durable root by default):
# AION_PHASE2_DB=data/aion/phase2.db
# AION_PAPER_DB=data/aion/paper_trading.db
# AION_SESSION_DB=data/aion/sessions.db
# AION_ACTIVATION_DIR=data/aion/activation
# Future managed DB (after cost approval):
# AION_DATABASE_URL=postgresql://...
```

## Migration (preserve live counters)

```bash
# Inspect only
python3 scripts/migrate_durable_storage.py --dry-run

# Copy /tmp live experiment DB → data/aion/ without resetting quotas
python3 scripts/migrate_durable_storage.py \
  --phase2-source /tmp/aion_phase2_live_experiment.db \
  --paper-source /tmp/aion_paper_trading.db \
  --activation-source /tmp/aion_activation
```

The migrator:

- Copies SQLite files into durable paths
- Verifies `autonomy_quota_events` counts and `risk_state` keys
- Writes `data/aion/last_migration.json`
- Backs up any existing destination under `data/aion/migration_backups/<timestamp>/`
- **Refuses** to overwrite a destination that is already larger than the source (anti-reset)

## Rollback

```bash
python3 scripts/migrate_durable_storage.py \
  --rollback data/aion/migration_backups/<timestamp>
```

Restores `phase2_before.db` / `paper_before.db` from that backup folder.

## Postgres (future)

1. Owner confirms **$10/mo** Supabase project (or provides another dedicated DB).
2. Create empty project `aion-ops` — never reuse YaliTek/Elaria projects.
3. Apply `aion/durable/postgres_schema.sql`.
4. Grant least-privilege role on schema `aion` only.
5. Set `AION_DATABASE_URL` (server-side only). SQLite remains supported until the Postgres adapter is activated in a follow-up.

## Paper trading market-data separation

Snapshots and trades store `price_source` and `is_live_market_data`.  
Official performance metrics use **live CoinGecko** rows only; mock/fallback rows are reported separately and cannot mark the experiment ready for live trading proposals.

## Threat assessment

| Threat | Mitigation |
|--------|------------|
| Quota reset during migrate | Size-guard + row-count verification; no DELETE of quota events |
| Writing into YaliTek/Elaria DBs | Explicit forbid; dedicated schema/project only |
| Secrets in git | `data/aion/`, `*.db`, `.env` gitignored |
| Ephemeral cloud disk | Document that true durability needs persistent volume or approved Postgres |

## Secrets (names only)

- None new for SQLite path
- Future: `AION_DATABASE_URL` (server-side only)
