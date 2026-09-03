-- AION dedicated Postgres schema (isolated).
-- Apply only to a dedicated AION database — never YaliTek/Elaria production DBs.
-- Owner must approve recurring cost before provisioning managed Postgres.
--
-- Expected monthly cost (Supabase new project via current org): $10/mo
-- Prefer: create project "aion-ops" with a least-privilege role limited to schema aion.

CREATE SCHEMA IF NOT EXISTS aion;

-- Mirror of SQLite logical model (TEXT timestamps ISO-8601 UTC).
CREATE TABLE IF NOT EXISTS aion.approvals (
  request_id TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  summary TEXT NOT NULL,
  destination TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  idempotency_key TEXT UNIQUE,
  decision TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  decided_at TEXT,
  decided_by TEXT,
  reason TEXT,
  approval_token_hash TEXT,
  token_consumed_at TEXT,
  executed_at TEXT,
  injection_flags_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS aion.audit_events (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  module TEXT NOT NULL,
  action TEXT NOT NULL,
  success BOOLEAN NOT NULL,
  detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.leads (
  lead_id TEXT PRIMARY KEY,
  source_url TEXT NOT NULL,
  requester_identity TEXT NOT NULL,
  stated_problem TEXT NOT NULL,
  relevant_service TEXT NOT NULL,
  fit_score DOUBLE PRECISION NOT NULL,
  confidence_score DOUBLE PRECISION NOT NULL,
  suggested_response TEXT NOT NULL,
  risks TEXT NOT NULL,
  approval_status TEXT NOT NULL,
  conversion_outcome TEXT NOT NULL,
  revenue_attributed DOUBLE PRECISION NOT NULL DEFAULT 0,
  raw_excerpt TEXT NOT NULL,
  created_at TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS aion.drafts (
  draft_id TEXT PRIMARY KEY,
  day_index INTEGER NOT NULL,
  theme TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  submolt TEXT NOT NULL,
  yalitek_connection TEXT,
  approval_request_id TEXT,
  created_at TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS aion.risk_state (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.autonomy_quota_events (
  id BIGSERIAL PRIMARY KEY,
  action TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_aion_quota_action_time
  ON aion.autonomy_quota_events(action, created_at);

CREATE TABLE IF NOT EXISTS aion.autonomy_blocks (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  action TEXT NOT NULL,
  reasons_json TEXT NOT NULL,
  payload_hash TEXT,
  detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.autonomy_actions (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  action TEXT NOT NULL,
  destination TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  idempotency_key TEXT UNIQUE,
  url TEXT,
  success BOOLEAN NOT NULL,
  detail_json TEXT NOT NULL,
  text_norm TEXT,
  account TEXT
);

CREATE TABLE IF NOT EXISTS aion.autonomy_account_interactions (
  id BIGSERIAL PRIMARY KEY,
  account TEXT NOT NULL,
  action TEXT NOT NULL,
  solicited BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.autonomy_rate_limits (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  action TEXT,
  status_code INTEGER,
  retry_after_seconds DOUBLE PRECISION,
  detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.daily_reports (
  report_date TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  body_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.lead_alerts (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  lead_id TEXT NOT NULL,
  detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.scheduler_locks (
  lock_name TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS aion.scheduler_state (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aion.health_alerts (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  alert_type TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  delivered BOOLEAN NOT NULL DEFAULT FALSE
);

-- Paper trading (same database, isolated tables)
CREATE TABLE IF NOT EXISTS aion.paper_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aion.paper_positions (
  asset TEXT PRIMARY KEY,
  qty DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS aion.paper_trades (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  asset TEXT NOT NULL,
  side TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  fee DOUBLE PRECISION NOT NULL,
  slippage DOUBLE PRECISION NOT NULL,
  note TEXT,
  price_source TEXT NOT NULL DEFAULT 'unknown',
  is_live_market_data BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS aion.paper_snapshots (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  equity DOUBLE PRECISION NOT NULL,
  cash DOUBLE PRECISION NOT NULL,
  btc_px DOUBLE PRECISION NOT NULL,
  eth_px DOUBLE PRECISION NOT NULL,
  detail_json TEXT NOT NULL,
  price_source TEXT NOT NULL DEFAULT 'unknown',
  is_live_market_data BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- Application-layer tables (created by runtime on first use; present in the
-- live Supabase export but absent from the original migration scripts).
-- Include here so that schema rebuilds from this file are complete.
-- ---------------------------------------------------------------------------

-- Conversation memory (durable chat sessions + long-term facts).
-- RLS is enabled on these three tables in production; no policies are
-- committed because row-level access is enforced at the application layer
-- via the aion_app role and never exposed publicly.
CREATE TABLE IF NOT EXISTS aion.conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_session_id TEXT NOT NULL,
  previous_response_id TEXT,
  model TEXT,
  runtime TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aion.conversation_messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES aion.conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED
);

CREATE TABLE IF NOT EXISTS aion.memory_facts (
  id BIGSERIAL PRIMARY KEY,
  content TEXT NOT NULL CHECK (length(btrim(content)) > 0),
  category TEXT,
  source_conversation_id UUID REFERENCES aion.conversations(id) ON DELETE SET NULL,
  source_message_id BIGINT REFERENCES aion.conversation_messages(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'forgotten', 'superseded')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  fts TSVECTOR GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(category, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(content, '')), 'B')
  ) STORED,
  superseded_by BIGINT REFERENCES aion.memory_facts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS memory_facts_active_updated_idx
  ON aion.memory_facts(updated_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS memory_facts_category_active_idx
  ON aion.memory_facts(category, updated_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS memory_facts_fts_idx
  ON aion.memory_facts USING gin(fts);

-- Lightweight key/value metadata store.
CREATE TABLE IF NOT EXISTS aion.meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Revenue ledger: payment orders created by Stripe checkout flow.
CREATE TABLE IF NOT EXISTS aion.payment_orders (
  order_id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  currency TEXT NOT NULL,
  customer_email TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending_owner_approval'
    CHECK (status IN ('pending_owner_approval', 'paid', 'fulfilled', 'cancelled', 'expired')),
  idempotency_key TEXT NOT NULL DEFAULT '',
  commercial_execution_id TEXT NOT NULL DEFAULT '',
  stripe_session_id TEXT NOT NULL DEFAULT '',
  stripe_checkout_url TEXT NOT NULL DEFAULT '',
  payment_intent_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_aion_payment_orders_idempotency
  ON aion.payment_orders(idempotency_key) WHERE idempotency_key <> '';
CREATE INDEX IF NOT EXISTS idx_aion_payment_orders_status_created
  ON aion.payment_orders(status, created_at DESC);

-- Paper-trading live positions (separate from paper_positions which are
-- scenario-specific; these track the current live-market paper book).
CREATE TABLE IF NOT EXISTS aion.positions (
  asset TEXT PRIMARY KEY,
  qty DOUBLE PRECISION NOT NULL
);

-- Live-market snapshots and trade log (mirrors paper_ tables for live market data).
CREATE TABLE IF NOT EXISTS aion.snapshots (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  equity DOUBLE PRECISION NOT NULL,
  cash DOUBLE PRECISION NOT NULL,
  btc_px DOUBLE PRECISION NOT NULL,
  eth_px DOUBLE PRECISION NOT NULL,
  detail_json TEXT NOT NULL,
  price_source TEXT NOT NULL DEFAULT 'unknown',
  is_live_market_data BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS aion.trades (
  id BIGSERIAL PRIMARY KEY,
  timestamp TEXT NOT NULL,
  asset TEXT NOT NULL,
  side TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  fee DOUBLE PRECISION NOT NULL,
  slippage DOUBLE PRECISION NOT NULL,
  note TEXT,
  price_source TEXT NOT NULL DEFAULT 'unknown',
  is_live_market_data BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- Least-privilege app role (password set out-of-band; never commit it).
-- ---------------------------------------------------------------------------
-- Pooler username form: aion_app.<project-ref>
-- GRANT CONNECT ON DATABASE postgres TO aion_app;
-- GRANT USAGE ON SCHEMA aion TO aion_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA aion TO aion_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA aion TO aion_app;
-- ALTER ROLE aion_app SET search_path TO aion, public;
