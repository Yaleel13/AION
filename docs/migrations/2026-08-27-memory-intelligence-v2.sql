-- AION memory intelligence v2
-- Applied to dedicated AION Supabase project gtviwpevltuqhygsbsou on 2026-08-27.

alter table aion.memory_facts
  drop constraint if exists memory_facts_status_check;

alter table aion.memory_facts
  add constraint memory_facts_status_check
  check (status in ('active', 'forgotten', 'superseded'));

alter table aion.memory_facts
  add column if not exists superseded_by bigint references aion.memory_facts(id) on delete set null;

create index if not exists memory_facts_category_active_idx
  on aion.memory_facts (category, updated_at desc)
  where status = 'active';

-- Deterministic category backfill only for previously uncategorized active memories.
update aion.memory_facts
set category = case
  when content ~* '\m(prefer|preference|like|dislike|style|tone|format)\M' then 'preference'
  when content ~* '\m(goal|objective|aim|working toward)\M' then 'goal'
  when content ~* '\m(project|repo|website|app|business|company)\M' then 'project'
  when content ~* '\m(always|never|must|constraint)\M' then 'constraint'
  else category
end,
updated_at = case
  when category is null and content ~* '\m(prefer|preference|like|dislike|style|tone|format|goal|objective|aim|working toward|project|repo|website|app|business|company|always|never|must|constraint)\M'
  then now()
  else updated_at
end
where status = 'active' and category is null;
