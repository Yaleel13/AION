"""Durable Opportunity Ledger storage.

Uses AION's existing durable database connection. The ledger is separate from
leads because an opportunity may originate from research, owned properties,
contracts, grants, or agent networks without being a sales lead.
"""

from __future__ import annotations

from typing import Any

from aion.durable.db import connect_phase2, database_url
from aion.moltbook.store import default_phase2_db_path
from aion.revenue_engine import Opportunity


class OpportunityStore:
    def __init__(self, path: str | None = None):
        self.path = path or default_phase2_db_path()
        self._conn = connect_phase2(self.path)
        self.backend = getattr(self._conn, "backend", "sqlite")
        if not database_url():
            self._init_sqlite_schema()

    def _init_sqlite_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
              opportunity_id TEXT PRIMARY KEY,
              discovered_at TEXT NOT NULL,
              scout TEXT NOT NULL,
              source TEXT NOT NULL,
              customer_problem TEXT NOT NULL,
              proposed_solution TEXT NOT NULL,
              estimated_revenue REAL NOT NULL,
              estimated_cost REAL NOT NULL DEFAULT 0,
              probability REAL NOT NULL,
              expected_value REAL NOT NULL,
              capital_required REAL NOT NULL DEFAULT 0,
              time_hours REAL NOT NULL DEFAULT 0,
              major_risks TEXT NOT NULL,
              ethical_considerations TEXT NOT NULL,
              confidence REAL NOT NULL,
              durable_value_score REAL NOT NULL,
              next_action TEXT NOT NULL,
              authorization_required TEXT NOT NULL,
              actual_result TEXT NOT NULL DEFAULT 'unresolved',
              realized_value REAL NOT NULL DEFAULT 0,
              UNIQUE(scout, source, customer_problem, proposed_solution)
            );
            CREATE INDEX IF NOT EXISTS idx_opportunities_rank
              ON opportunities(durable_value_score DESC, discovered_at DESC);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert(self, opportunity: Opportunity) -> None:
        row = opportunity.to_row()
        self._conn.execute(
            """
            INSERT INTO opportunities (
              opportunity_id, discovered_at, scout, source, customer_problem,
              proposed_solution, estimated_revenue, estimated_cost, probability,
              expected_value, capital_required, time_hours, major_risks,
              ethical_considerations, confidence, durable_value_score, next_action,
              authorization_required, actual_result, realized_value
            ) VALUES (
              :opportunity_id, :discovered_at, :scout, :source, :customer_problem,
              :proposed_solution, :estimated_revenue, :estimated_cost, :probability,
              :expected_value, :capital_required, :time_hours, :major_risks,
              :ethical_considerations, :confidence, :durable_value_score, :next_action,
              :authorization_required, :actual_result, :realized_value
            )
            ON CONFLICT(opportunity_id) DO UPDATE SET
              estimated_revenue=excluded.estimated_revenue,
              estimated_cost=excluded.estimated_cost,
              probability=excluded.probability,
              expected_value=excluded.expected_value,
              confidence=excluded.confidence,
              durable_value_score=excluded.durable_value_score,
              next_action=excluded.next_action,
              authorization_required=excluded.authorization_required
            """,
            row,
        )
        self._conn.commit()

    def top(self, *, limit: int = 25) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """SELECT * FROM opportunities
               ORDER BY durable_value_score DESC, discovered_at DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def record_result(self, opportunity_id: str, *, result: str, realized_value: float = 0.0) -> None:
        self._conn.execute(
            "UPDATE opportunities SET actual_result = ?, realized_value = ? WHERE opportunity_id = ?",
            (result, float(realized_value), opportunity_id),
        )
        self._conn.commit()
