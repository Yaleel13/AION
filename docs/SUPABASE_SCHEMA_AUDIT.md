# Supabase Schema Audit

**Date:** 2026-09-01
**Project:** `gtviwpevltuqhygsbsou` (AION, West US/Oregon)
**Scope:** Read-only production inventory
**Schema export:** [supabase/aion_schema.sql](../supabase/aion_schema.sql), SHA-256 `58F0353820E8B01B09EB1B021B926554973A5DAB4DBA51191794663A3EC6E547`

## Verified

- The local Supabase workspace is linked to the dedicated AION project.
- Production runtime status reports a configured Postgres backend in schema `aion` with 27 tables.
- The linked database has 12 applied remote migrations:

```text
20260827183311
20260827184145
20260827184556
20260827185040
20260827185105
20260827204253
20260827204438
20260827225147
20260827225634
20260827230541
20260827230907
20260831035005
```

- `supabase inspect db table-stats --linked` confirmed these `aion` tables:

```text
approvals
audit_events
autonomy_account_interactions
autonomy_actions
autonomy_blocks
autonomy_quota_events
autonomy_rate_limits
conversation_messages
conversations
daily_reports
drafts
health_alerts
lead_alerts
leads
memory_facts
meta
opportunities
paper_meta
paper_positions
paper_snapshots
paper_trades
positions
risk_state
scheduler_locks
scheduler_state
snapshots
trades
```

- Tables holding active data include `opportunities` (213 estimated rows), `leads` (127), `audit_events` (381), `snapshots` (444), `daily_reports` (5), `drafts` (14), and `approvals` (10).
- A full `aion` schema export completed successfully on 2026-09-01 after Docker Desktop became available.
- RLS is enabled on `conversations`, `conversation_messages`, and `memory_facts`. No policies are present in the exported `aion` schema.
- The export contains no views, functions, or `SECURITY DEFINER` routines in schema `aion`.
- Schema/table/sequence grants are limited to the dedicated `aion_app` role.

## Repository Comparison

The committed reference schema is [aion/durable/postgres_schema.sql](../aion/durable/postgres_schema.sql). All 19 tables in that reference exist in the live schema. The live schema additionally contains eight application-facing tables: `conversation_messages`, `conversations`, `memory_facts`, `meta`, `opportunities`, `positions`, `snapshots`, and `trades`.

This is a verified repository-versus-live inventory difference. The schema export provides the current source of truth for a future migration reconciliation; no remote schema changes were made during this audit.

## Index Findings

- The ranking, lead content-hash, opportunity primary-key, metadata, risk-state, and quota indexes show active usage.
- Several indexes report no scans on empty or near-empty tables. This is expected at the current data volume and is not a removal recommendation.
- `autonomy_quota_events` has two equivalent indexes on `(action, created_at)`: `idx_aion_quota_action_time` and `idx_autonomy_quota_action_time`. Confirm their definitions against the applied migration history before removing either one.

## Follow-up

The local Supabase workspace has no migration files, while the remote project has 12 applied migrations. Reconstruct or pull the migration history before making schema changes, then use a reviewed migration to reconcile any approved differences.

For a refreshed audit:

```powershell
supabase db dump --linked --schema aion --file supabase/aion_schema.sql
supabase inspect db index-stats --linked
```
