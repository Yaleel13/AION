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


def _serverless_runtime() -> bool:
    """Return true when local SQLite cannot honestly be called durable."""
    return bool(
        os.getenv("VERCEL")
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("FUNCTIONS_WORKER_RUNTIME")
    )


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
        if _serverless_runtime():
            return DbStatus(
                backend="sqlite_ephemeral",
                configured=False,
                schema=None,
                detail=(
                    "AION_DATABASE_URL unset on serverless runtime; local SQLite "
                    "may be discarded between invocations"
                ),
            )
        return DbStatus(
            backend="sqlite",
            configured=True,
            schema=None,
            detail="AION_DATABASE_URL unset; using SQLite under AION_DATA_DIR",
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


def _adapt_sql(sql: str, params: Any = None) -> tuple[str, Any]:
    """Adapt sqlite-ish placeholders for psycopg."""
    if params is None:
        return sql.replace("?", "%s"), None
    if isinstance(params, dict):
        return _NAMED_PARAM.sub(r"%(\1)s", sql), params
    return sql.replace("?", "%s"), params


def connect_postgres(url: str | None = None) -> PostgresConn:
    dsn = url or database_url()
    if not dsn:
        raise RuntimeError("AION_DATABASE_URL is not configured")
    if not _is_postgres_url(dsn):
        raise RuntimeError("AION_DATABASE_URL must use postgresql://")
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - dependency failure
        raise RuntimeError("psycopg is required for Postgres durable storage") from exc
    conn = psycopg.connect(dsn, row_factory=dict_row)
    conn.execute("SET search_path TO aion, public")
    return PostgresConn(conn)


def connect_sqlite(path: str) -> SqliteConn:
    return SqliteConn(path)


def connect(path: str | None = None):
    url = database_url()
    if url:
        return connect_postgres(url)
    if not path:
        raise ValueError("SQLite path is required when AION_DATABASE_URL is unset")
    return connect_sqlite(path)


def execute_many(conn: Any, sql: str, rows: Iterable[Sequence[Any]]) -> None:
    """Portable executemany for sqlite / psycopg wrappers."""
    cur = conn.cursor()
    try:
        sql2 = sql if getattr(conn, "backend", "sqlite") == "sqlite" else sql.replace("?", "%s")
        for row in rows:
            cur.execute(sql2, row)
    finally:
        try:
            cur.close()
        except Exception:
            pass
