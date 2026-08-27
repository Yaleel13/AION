"""Database connection factory for AION durable storage.

Uses SQLite under ``AION_DATA_DIR`` by default. When ``AION_DATABASE_URL`` is set
(Postgres / Supabase), connections target schema ``aion`` only.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse


_NAMED_PARAM = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def database_url() -> str | None:
    raw = (os.getenv("AION_DATABASE_URL") or "").strip()
    return raw or None


def storage_backend() -> str:
    return "postgres" if database_url() else "sqlite"


def _is_postgres_url(url: str) -> bool:
    scheme = urlparse(url).scheme.lower()
    return scheme in {"postgres", "postgresql", "postgresql+psycopg"}


@dataclass
class DbStatus:
    backend: str
    configured: bool
    schema: str | None = None
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "configured": self.configured,
            "schema": self.schema,
            "detail": self.detail,
        }


def storage_status() -> DbStatus:
    url = database_url()
    if not url:
        return DbStatus(
            backend="sqlite",
            configured=True,
            schema=None,
            detail="AION_DATABASE_URL unset; using durable SQLite files",
        )
    if not _is_postgres_url(url):
        return DbStatus(
            backend="postgres",
            configured=False,
            schema="aion",
            detail="AION_DATABASE_URL must be a postgresql:// URL",
        )
    try:
        conn = connect_postgres(url)
        try:
            row = conn.execute(
                "SELECT count(*) AS c FROM information_schema.tables "
                "WHERE table_schema = 'aion'"
            ).fetchone()
            count = int(row["c"] if isinstance(row, dict) else row[0])
        finally:
            conn.close()
        return DbStatus(
            backend="postgres",
            configured=True,
            schema="aion",
            detail=f"connected; {count} tables in schema aion",
        )
    except Exception as exc:  # noqa: BLE001 — surface status without crashing callers
        return DbStatus(
            backend="postgres",
            configured=False,
            schema="aion",
            detail=f"connection failed: {exc}",
        )


class _PgCursor:
    def __init__(self, cur: Any):
        self._cur = cur
        self.lastrowid = None

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys"):
            return row
        return row

    def fetchall(self):
        return list(self._cur.fetchall())

    def execute(self, sql: str, params: Any = None):
        sql2, params2 = _adapt_sql(sql, params)
        self._cur.execute(sql2, params2)
        self.lastrowid = None
        return self

    def executescript(self, script: str):
        # Schema is managed via migrations on Postgres; ignore SQLite DDL scripts.
        return self

    def close(self):
        self._cur.close()


class PostgresConn:
    """psycopg connection wrapper with sqlite-like ``?`` / ``:name`` placeholders."""

    def __init__(self, conn: Any):
        self._conn = conn
        self.path = "postgres:aion"
        self.backend = "postgres"

    def execute(self, sql: str, params: Any = None):
        cur = self._conn.cursor()
        sql2, params2 = _adapt_sql(sql, params)
        cur.execute(sql2, params2)
        wrapper = _PgCursor(cur)
        # Best-effort lastrowid for INSERT … RETURNING id callers.
        if cur.description is None and "RETURNING" not in sql2.upper():
            wrapper.lastrowid = None
        elif cur.description is not None:
            # Caller may fetch; keep cursor open on returned wrapper
            pass
        return wrapper

    def executescript(self, script: str):
        return None

    def cursor(self):
        return _PgCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def begin_immediate(self):
        self._conn.execute("BEGIN")


class SqliteConn:
    def __init__(self, path: str):
        self.path = path
        self.backend = "sqlite"
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def execute(self, sql: str, params: Any = None):
        if params is None:
            return self._conn.execute(sql)
        return self._conn.execute(sql, params)

    def executescript(self, script: str):
        return self._conn.executescript(script)

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def begin_immediate(self):
        self._conn.execute("BEGIN IMMEDIATE")


def _adapt_sql(sql: str, params: Any) -> tuple[str, Any]:
    """Translate sqlite-style placeholders to psycopg pyformat."""
    if sql.strip().upper() == "BEGIN IMMEDIATE":
        sql = "BEGIN"
    if params is None:
        return sql.replace("?", "%s"), params

    if isinstance(params, dict):
        # :name → %(name)s
        sql2 = _NAMED_PARAM.sub(r"%(\1)s", sql)
        sql2 = sql2.replace("?", "%s")  # shouldn't mix, but be safe
        return sql2, params

    if isinstance(params, (list, tuple)):
        return sql.replace("?", "%s"), params

    return sql.replace("?", "%s"), params


def connect_postgres(url: str | None = None) -> PostgresConn:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "psycopg is required for AION_DATABASE_URL. Install: pip install 'psycopg[binary]'"
        ) from exc

    raw = url or database_url()
    if not raw:
        raise RuntimeError("AION_DATABASE_URL is not set")

    # Normalize SQLAlchemy-style URLs if pasted by mistake.
    raw = raw.replace("postgresql+psycopg://", "postgresql://", 1)
    conn = psycopg.connect(raw, row_factory=dict_row, options="-c search_path=aion,public")
    conn.execute("SET search_path TO aion, public")
    return PostgresConn(conn)


def connect_sqlite(path: str) -> SqliteConn:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return SqliteConn(path)


def connect_phase2(sqlite_path: str | None = None) -> SqliteConn | PostgresConn:
    url = database_url()
    if url:
        return connect_postgres(url)
    if not sqlite_path:
        raise ValueError("sqlite_path required when AION_DATABASE_URL is unset")
    return connect_sqlite(sqlite_path)


def connect_paper(sqlite_path: str | None = None) -> SqliteConn | PostgresConn:
    """Paper trading uses the same Postgres when configured; else its own SQLite file."""
    return connect_phase2(sqlite_path)
