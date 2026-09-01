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

    def record_payment_order(
        self,
        *,
        order_id: str,
        opportunity_id: str,
        amount_cents: int,
        currency: str,
        customer_email: str = "",
        status: str = "pending_owner_approval",
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        # Ensure table exists
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_orders (
              order_id TEXT PRIMARY KEY,
              opportunity_id TEXT NOT NULL,
              amount_cents INTEGER NOT NULL,
              currency TEXT NOT NULL,
              customer_email TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'pending_owner_approval',
              created_at TEXT NOT NULL
            )
            """
        )

        # Try to add missing columns to existing tables (idempotent migration)
        # Note: Can't add UNIQUE via ALTER TABLE on existing table, so we add nullable columns
        for col_def in [
            "idempotency_key TEXT",  # No UNIQUE constraint for ALTER compatibility
            "updated_at TEXT",
            "stripe_session_id TEXT",
            "stripe_checkout_url TEXT",
            "payment_intent_id TEXT",
        ]:
            try:
                self._conn.execute(f"ALTER TABLE payment_orders ADD COLUMN {col_def}")
            except Exception:
                pass  # Column already exists, that's fine

        # Insert the base payment order (always works, uses base columns)
        self._conn.execute(
            """
            INSERT INTO payment_orders (
              order_id, opportunity_id, amount_cents, currency, customer_email,
              status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(order_id) DO UPDATE SET
              opportunity_id=excluded.opportunity_id,
              amount_cents=excluded.amount_cents,
              currency=excluded.currency,
              customer_email=excluded.customer_email,
              status=excluded.status
            """,
            (
                order_id,
                opportunity_id,
                int(amount_cents),
                str(currency).lower(),
                customer_email,
                status,
            ),
        )

        # Now update with optional columns if they exist and we have values
        if idempotency_key:
            try:
                self._conn.execute(
                    "UPDATE payment_orders SET idempotency_key = ?, updated_at = datetime('now') WHERE order_id = ?",
                    (idempotency_key, order_id),
                )
            except Exception:
                pass  # Column might not exist, that's fine (graceful degradation)

        # Always update updated_at to current timestamp
        try:
            self._conn.execute(
                "UPDATE payment_orders SET updated_at = datetime('now') WHERE order_id = ?",
                (order_id,),
            )
        except Exception:
            pass  # Column might not exist

        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM payment_orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        return dict(row) if row else {"order_id": order_id, "status": status}

    def list_payment_orders(self, *, limit: int = 25) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM payment_orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def idempotency_key_exists(self, idempotency_key: str) -> bool:
        """Check if an idempotency_key has already been processed (webhook replay protection)."""
        if not idempotency_key:
            return False
        try:
            row = self._conn.execute(
                "SELECT 1 FROM payment_orders WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return row is not None
        except Exception:
            # If the column doesn't exist, return False (graceful degradation)
            return False

    def record_revenue_attribution(self, order_id: str, opportunity_id: str, commercial_execution_id: str = "") -> bool:
        """Record that a payment order is attributed to a commercial execution.

        This links a payment result back to the commercial opportunity that generated it.

        Args:
            order_id: Payment order ID
            opportunity_id: Opportunity ID
            commercial_execution_id: ID of the commercial execution (optional)

        Returns:
            True if attribution recorded successfully
        """
        if not order_id:
            return False

        # Ensure column exists for revenue attribution
        try:
            self._conn.execute(
                "ALTER TABLE payment_orders ADD COLUMN commercial_execution_id TEXT"
            )
        except Exception:
            pass  # Column already exists

        try:
            # Update the payment order with commercial execution attribution
            self._conn.execute(
                """
                UPDATE payment_orders
                SET commercial_execution_id = ?, updated_at = datetime('now')
                WHERE order_id = ?
                """,
                (commercial_execution_id, order_id),
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def get_revenue_by_execution(self, opportunity_id: str = "") -> list[dict[str, Any]]:
        """Get attributed revenue grouped by commercial execution.

        Returns list of dicts with:
        - commercial_execution_id
        - opportunity_id
        - total_amount_cents
        - order_count
        - fulfilled_amount_cents
        """
        try:
            # Try to query with commercial_execution_id column
            query = """
            SELECT
                commercial_execution_id,
                opportunity_id,
                SUM(CASE WHEN status = 'fulfilled' THEN amount_cents ELSE 0 END) as fulfilled_amount_cents,
                SUM(amount_cents) as total_amount_cents,
                COUNT(*) as order_count
            FROM payment_orders
            WHERE status IN ('paid', 'fulfilled')
            """
            params: list[Any] = []
            if opportunity_id:
                query += " AND opportunity_id = ?"
                params.append(opportunity_id)

            query += " GROUP BY commercial_execution_id, opportunity_id"

            rows = self._conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        except Exception:
            # Column doesn't exist, return empty list (graceful degradation)
            return []
