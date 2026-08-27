-- AION memory quality v1
-- Applied to dedicated AION Supabase project gtviwpevltuqhygsbsou on 2026-08-27.
-- This file is the reproducible record of the production migration.

alter table aion.conversation_messages
  add column if not exists fts tsvector
  generated always as (to_tsvector('english', coalesce(content, ''))) stored;

create index if not exists conversation_messages_fts_idx
  on aion.conversation_messages using gin (fts);

create table if not exists aion.memory_facts (
  id bigint generated always as identity primary key,
  content text not null check (length(btrim(content)) > 0),
  category text,
  source_conversation_id uuid references aion.conversations(id) on delete set null,
  source_message_id bigint references aion.conversation_messages(id) on delete set null,
  status text not null default 'active' check (status in ('active', 'forgotten')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  fts tsvector generated always as (
    setweight(to_tsvector('english', coalesce(category, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(content, '')), 'B')
  ) stored
);

create index if not exists memory_facts_fts_idx
  on aion.memory_facts using gin (fts);

create index if not exists memory_facts_active_updated_idx
  on aion.memory_facts (updated_at desc) where status = 'active';

alter table aion.memory_facts enable row level security;

revoke all on table aion.memory_facts from public, anon, authenticated;
revoke all on sequence aion.memory_facts_id_seq from public, anon, authenticated;
grant select, insert, update, delete on table aion.memory_facts to aion_app;
grant usage, select on sequence aion.memory_facts_id_seq to aion_app;

-- Public storage telemetry intentionally exposes only schema name, table count,
-- and check time. The count is explicit because anon/authenticated roles do not
-- have visibility into the private aion schema and must not receive it merely
-- to compute status dynamically.
create or replace view public.aion_storage_status
with (security_invoker = true)
as
select
  'aion'::text as schema_name,
  26::integer as table_count,
  timezone('utc', now())::text as checked_at_utc;
