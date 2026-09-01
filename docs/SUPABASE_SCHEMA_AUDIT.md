# Supabase Schema Audit

**Date:** 2026-09-01
**Project:** `gtviwpevltuqhygsbsou` (AION, West US/Oregon)
**Scope:** Read-only production inventory

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

## Repository Comparison

The committed reference schema is [aion/durable/postgres_schema.sql](../aion/durable/postgres_schema.sql). It covers the Phase 2, scheduler, audit, and paper-trading tables, while the live database additionally contains application-facing opportunity, conversation, memory, metadata, snapshot, position, and trade tables.

This is a verified repository-versus-live inventory difference. It is not yet classified as drift requiring a migration because the remote migration DDL has not been exported for column, index, view, function, trigger, grant, or RLS comparison.

## Pending Evidence

A full schema dump with `supabase db dump --linked --schema aion` is blocked on this workstation because Supabase CLI v2.39.2 invokes its Postgres Docker image and Docker Desktop is not installed. Native `psql` and `pg_dump` are also unavailable.

Complete the DDL-level audit after installing and starting Docker Desktop, then run:

```powershell
supabase db dump --linked --schema aion --file supabase/aion_schema.sql
supabase inspect db index-stats --linked
```

Compare the export with the committed schema and document views, functions, triggers, indexes, grants, and RLS policies before making any migration changes.
