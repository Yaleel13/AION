# AION Durable Storage

**Status:** SQLite under `AION_DATA_DIR` is the active runtime store. Dedicated Supabase Postgres is **provisioned** with schema `aion` applied; the Postgres adapter is not wired into the app yet.

## Selected infrastructure

| Layer | Choice | Monthly cost | Notes |
|-------|--------|--------------|-------|
| Default durable files | SQLite under `AION_DATA_DIR` (default `data/aion/`) | **$0** | Survives process restart if the volume is persistent |
| Managed Postgres | Dedicated Supabase project **AION** (`gtviwpevltuqhygsbsou`), schema `aion` | Owner project | Provisioned 2026-08-27 · region `us-west-2` · https://gtviwpevltuqhygsbsou.supabase.co |
| Forbidden | YaliTekonline / Elaria Supabase projects | — | AION must not touch those tables |

Least privilege: use a role limited to schema `aion` only for app connections.

## Environment

```bash
AION_DATA_DIR=data/aion          # durable root (gitignored)
# Optional overrides (still under durable root by default):
# AION_PHASE2_DB=data/aion/phase2.db
# AION_PAPER_DB=data/aion/paper_trading.db
# AION_SESSION_DB=data/aion/sessions.db
# AION_ACTIVATION_DIR=data/aion/activation
# Managed Postgres (server-side only; never commit the password):
# AION_DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-us-west-2.pooler.supabase.com:6543/postgres
# Project: https://gtviwpevltuqhygsbsou.supabase.co
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

## Postgres (provisioned; adapter pending)

1. Dedicated project **AION** created — never reuse YaliTek/Elaria projects. ✅
2. Applied `aion/durable/postgres_schema.sql` → schema `aion` (approvals, audit, leads, drafts, autonomy, scheduler, paper trading). ✅
3. Set `AION_DATABASE_URL` from the Supabase dashboard connection string (server-side / secret store only). ⏳
4. Activate the Postgres adapter in app code (follow-up). Until then, runtime still uses SQLite under `AION_DATA_DIR`.
5. Prefer a least-privilege DB role limited to schema `aion`.

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
- `AION_DATABASE_URL` (server-side only; do not commit)
