create table if not exists aion.payment_orders (
  order_id text primary key,
  opportunity_id text not null,
  amount_cents integer not null check (amount_cents > 0),
  currency text not null,
  customer_email text not null default '',
  status text not null default 'pending_owner_approval'
    check (status in ('pending_owner_approval', 'paid', 'fulfilled', 'cancelled', 'expired')),
  idempotency_key text not null default '',
  commercial_execution_id text not null default '',
  stripe_session_id text not null default '',
  stripe_checkout_url text not null default '',
  payment_intent_id text not null default '',
  created_at text not null,
  updated_at text not null
);

create unique index if not exists idx_aion_payment_orders_idempotency
  on aion.payment_orders (idempotency_key)
  where idempotency_key <> '';

create index if not exists idx_aion_payment_orders_status_created
  on aion.payment_orders (status, created_at desc);

alter table aion.payment_orders enable row level security;

revoke all on table aion.payment_orders from anon, authenticated, public;
grant select, insert, update, delete on table aion.payment_orders to aion_app;
