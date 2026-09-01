from __future__ import annotations

from aion.paper_trading.engine import PaperConfig, PaperTradingEngine


class _PostgresConnection:
    backend = "postgres"

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, sql: str, *args, **kwargs):
        self.executed.append(sql)
        raise AssertionError("Postgres runtime initialization must not execute DDL")


def test_paper_engine_does_not_run_postgres_ddl(monkeypatch, tmp_path):
    connection = _PostgresConnection()
    monkeypatch.setenv("AION_DATABASE_URL", "postgresql://example.invalid/postgres")
    monkeypatch.setattr("aion.durable.db.connect_paper", lambda _path: connection)

    engine = PaperTradingEngine(PaperConfig(db_path=str(tmp_path / "paper.db")))

    assert engine._conn is connection
    assert connection.executed == []
