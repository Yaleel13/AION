-- AION Revenue Engine v1 schema extension.
-- Apply only to the dedicated AION database. Never apply to YaliTek/Elaria.

CREATE SCHEMA IF NOT EXISTS aion;

CREATE TABLE IF NOT EXISTS aion.opportunities (
  opportunity_id TEXT PRIMARY KEY,
  discovered_at TEXT NOT NULL,
  scout TEXT NOT NULL,
  source TEXT NOT NULL,
  customer_problem TEXT NOT NULL,
  proposed_solution TEXT NOT NULL,
  estimated_revenue DOUBLE PRECISION NOT NULL,
  estimated_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
  probability DOUBLE PRECISION NOT NULL,
  expected_value DOUBLE PRECISION NOT NULL,
  capital_required DOUBLE PRECISION NOT NULL DEFAULT 0,
  time_hours DOUBLE PRECISION NOT NULL DEFAULT 0,
  major_risks TEXT NOT NULL,
  ethical_considerations TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  durable_value_score DOUBLE PRECISION NOT NULL,
  next_action TEXT NOT NULL,
  authorization_required TEXT NOT NULL,
  actual_result TEXT NOT NULL DEFAULT 'unresolved',
  realized_value DOUBLE PRECISION NOT NULL DEFAULT 0,
  UNIQUE(scout, source, customer_problem, proposed_solution)
);

CREATE INDEX IF NOT EXISTS idx_aion_opportunities_rank
  ON aion.opportunities(durable_value_score DESC, discovered_at DESC);
