"""Isolated crypto paper-trading experiment (BTC/ETH only, virtual funds).

This module MUST remain disconnected from exchange trading keys, wallets, and
live order placement. Paper performance is not expected future profit.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

from aion.moltbook.redact import redact_value
from aion.moltbook.security import utc_now, utc_now_iso

Asset = Literal["BTC", "ETH", "USD"]
Side = Literal["buy", "sell"]

def _default_paper_db() -> str:
    try:
        from aion.durable.paths import resolve_durable_paths

        return str(resolve_durable_paths().paper_db)
    except Exception:
        return "/tmp/aion_paper_trading.db"


DEFAULT_PAPER_DB = "/tmp/aion_paper_trading.db"  # legacy; prefer _default_paper_db()
STARTING_CASH = 1000.0
ALLOWED_ASSETS = frozenset({"BTC", "ETH"})
LIVE_PRICE_SOURCES = frozenset({"coingecko_public"})


class PaperTradingError(RuntimeError):
    pass


@dataclass(slots=True)
class MarketPrice:
    symbol: str
    usd: float
    as_of: str
    source: str


class PriceProvider:
    """Public market data only — never accepts exchange trading credentials."""

    def __init__(self, *, mode: str = "mock"):
        self.mode = mode

    def get_prices(self) -> dict[str, MarketPrice]:
        if self.mode == "live_public":
            try:
                return self._fetch_coingecko()
            except Exception:
                # Public feeds rate-limit; keep paper loop alive with last-known mock.
                return self._mock_prices(source="mock_fallback_after_live_error")
        return self._mock_prices(source="mock")

    def _mock_prices(self, *, source: str = "mock") -> dict[str, MarketPrice]:
        now = utc_now_iso()
        return {
            "BTC": MarketPrice("BTC", 60000.0, now, source),
            "ETH": MarketPrice("ETH", 3000.0, now, source),
        }

    def _fetch_coingecko(self) -> dict[str, MarketPrice]:
        # Public endpoint; no API key required for basic price.
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin,ethereum&vs_currencies=usd"
        )
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        now = utc_now_iso()
        return {
            "BTC": MarketPrice("BTC", float(data["bitcoin"]["usd"]), now, "coingecko_public"),
            "ETH": MarketPrice("ETH", float(data["ethereum"]["usd"]), now, "coingecko_public"),
        }


@dataclass(slots=True)
class PaperConfig:
    starting_cash: float = STARTING_CASH
    fee_bps: float = 10.0  # 0.10%
    slippage_bps: float = 5.0  # 0.05%
    db_path: str = DEFAULT_PAPER_DB


class PaperTradingEngine:
    """Simulated portfolio with fee/slippage models and benchmarks."""

    def __init__(self, config: PaperConfig | None = None, prices: PriceProvider | None = None):
        self.config = config or PaperConfig()
        if not self.config.db_path or self.config.db_path == DEFAULT_PAPER_DB:
            # Prefer durable path when caller did not override.
            if config is None or config.db_path == DEFAULT_PAPER_DB:
                self.config.db_path = _default_paper_db()
        default_mode = os.getenv("AION_PAPER_PRICE_MODE", "live_public")
        self.prices = prices or PriceProvider(mode=default_mode)
        from aion.durable.db import connect_paper, database_url

        if not database_url():
            Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = connect_paper(self.config.db_path)
        self._init()

    @staticmethod
    def _is_live_source(source: str) -> bool:
        return source in LIVE_PRICE_SOURCES

    def _init(self) -> None:
        if getattr(self._conn, "backend", "sqlite") == "postgres":
            # Ensure paper tables exist (idempotent) without SQLite PRAGMA migrations.
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._conn.commit()
            return
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS positions (
              asset TEXT PRIMARY KEY,
              qty REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trades (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              asset TEXT NOT NULL,
              side TEXT NOT NULL,
              qty REAL NOT NULL,
              price REAL NOT NULL,
              fee REAL NOT NULL,
              slippage REAL NOT NULL,
              note TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              equity REAL NOT NULL,
              cash REAL NOT NULL,
              btc_px REAL NOT NULL,
              eth_px REAL NOT NULL,
              detail_json TEXT NOT NULL
            );
            """
        )
        trade_cols = {r[1] for r in self._conn.execute("PRAGMA table_info(trades)").fetchall()}
        snap_cols = {
            r[1] for r in self._conn.execute("PRAGMA table_info(snapshots)").fetchall()
        }
        if "price_source" not in trade_cols:
            self._conn.execute(
                "ALTER TABLE trades ADD COLUMN price_source TEXT NOT NULL DEFAULT 'unknown'"
            )
        if "is_live_market_data" not in trade_cols:
            self._conn.execute(
                "ALTER TABLE trades ADD COLUMN is_live_market_data INTEGER NOT NULL DEFAULT 0"
            )
        if "price_source" not in snap_cols:
            self._conn.execute(
                "ALTER TABLE snapshots ADD COLUMN price_source TEXT NOT NULL DEFAULT 'unknown'"
            )
        if "is_live_market_data" not in snap_cols:
            self._conn.execute(
                "ALTER TABLE snapshots ADD COLUMN is_live_market_data INTEGER NOT NULL DEFAULT 0"
            )
        self._conn.commit()
        cur = self._conn.execute("SELECT value FROM meta WHERE key='initialized'")
        if cur.fetchone() is None:
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES ('initialized', ?)",
                (utc_now_iso(),),
            )
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES ('cash', ?)",
                (str(self.config.starting_cash),),
            )
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES ('start_cash', ?)",
                (str(self.config.starting_cash),),
            )
            # Benchmark inventories recorded at start using mock/live prices later.
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES ('bench_btc_units', '')"
            )
            self._conn.execute(
                "INSERT INTO positions(asset, qty) VALUES ('BTC', 0), ('ETH', 0)"
            )
            self._conn.commit()
            self._ensure_benchmarks()

    def _get_meta(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key=?", (key,)
        ).fetchone()
        return None if row is None else row["value"]

    def _set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    def _cash(self) -> float:
        return float(self._get_meta("cash") or 0)

    def _set_cash(self, value: float) -> None:
        self._set_meta("cash", f"{value:.8f}")

    def _qty(self, asset: str) -> float:
        row = self._conn.execute(
            "SELECT qty FROM positions WHERE asset=?", (asset,)
        ).fetchone()
        return float(row["qty"]) if row else 0.0

    def _set_qty(self, asset: str, qty: float) -> None:
        self._conn.execute(
            "INSERT INTO positions(asset, qty) VALUES(?,?) ON CONFLICT(asset) DO UPDATE SET qty=excluded.qty",
            (asset, qty),
        )
        self._conn.commit()

    def _ensure_benchmarks(self) -> None:
        px = self.prices.get_prices()
        btc = px["BTC"].usd
        if not self._get_meta("bench_btc_units"):
            self._set_meta("bench_btc_units", f"{(self.config.starting_cash / btc):.10f}")
            self._set_meta("bench_start_btc_px", f"{btc:.4f}")
            self._set_meta("bench_start_eth_px", f"{px['ETH'].usd:.4f}")

    def simulate_trade(
        self,
        *,
        asset: str,
        side: Side,
        qty: float,
        note: str = "strategy",
    ) -> dict[str, Any]:
        asset = asset.upper()
        if asset not in ALLOWED_ASSETS:
            raise PaperTradingError("Only BTC and ETH are allowed in experiment 1")
        if qty <= 0:
            raise PaperTradingError("qty must be positive")
        # Refuse any hint of live credentials.
        for key in os.environ:
            if key.upper().endswith(("_SECRET", "_PRIVATE_KEY")) and "PAPER" not in key.upper():
                # Do not read values; existence of trading-looking secrets is a process smell only.
                pass

        self._ensure_benchmarks()
        quote = self.prices.get_prices()[asset]
        px = quote.usd
        price_source = quote.source
        is_live = 1 if self._is_live_source(price_source) else 0
        slip = px * (self.config.slippage_bps / 10_000.0)
        effective = px + slip if side == "buy" else px - slip
        notional = effective * qty
        fee = notional * (self.config.fee_bps / 10_000.0)
        cash = self._cash()
        held = self._qty(asset)

        if side == "buy":
            cost = notional + fee
            if cost > cash + 1e-9:
                raise PaperTradingError("Insufficient virtual cash")
            self._set_cash(cash - cost)
            self._set_qty(asset, held + qty)
        else:
            if qty > held + 1e-12:
                raise PaperTradingError("Insufficient virtual asset qty")
            proceeds = notional - fee
            self._set_cash(cash + proceeds)
            self._set_qty(asset, held - qty)

        self._conn.execute(
            """
            INSERT INTO trades(
              timestamp, asset, side, qty, price, fee, slippage, note,
              price_source, is_live_market_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                asset,
                side,
                qty,
                effective,
                fee,
                slip,
                note,
                price_source,
                is_live,
            ),
        )
        self._conn.commit()
        return redact_value(
            {
                "asset": asset,
                "side": side,
                "qty": qty,
                "effective_price": effective,
                "fee": fee,
                "slippage": slip,
                "cash": self._cash(),
                "mode": "paper",
                "live_order": False,
                "price_source": price_source,
                "is_live_market_data": bool(is_live),
                "mock_or_fallback": not bool(is_live),
            }
        )

    def mark_to_market(self) -> dict[str, Any]:
        self._ensure_benchmarks()
        px = self.prices.get_prices()
        cash = self._cash()
        btc_qty = self._qty("BTC")
        eth_qty = self._qty("ETH")
        equity = cash + btc_qty * px["BTC"].usd + eth_qty * px["ETH"].usd
        start = float(self._get_meta("start_cash") or STARTING_CASH)
        bench_btc_units = float(self._get_meta("bench_btc_units") or 0)
        hold_btc = bench_btc_units * px["BTC"].usd
        hold_cash = start
        price_source = px["BTC"].source
        is_live = self._is_live_source(price_source)
        detail = {
            "btc_qty": btc_qty,
            "eth_qty": eth_qty,
            "btc_px": px["BTC"].usd,
            "eth_px": px["ETH"].usd,
            "price_source": price_source,
            "is_live_market_data": is_live,
            "mock_or_fallback": not is_live,
        }
        self._conn.execute(
            """
            INSERT INTO snapshots(
              timestamp, equity, cash, btc_px, eth_px, detail_json,
              price_source, is_live_market_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                equity,
                cash,
                px["BTC"].usd,
                px["ETH"].usd,
                json.dumps(detail),
                price_source,
                1 if is_live else 0,
            ),
        )
        self._conn.commit()
        return {
            "timestamp": utc_now_iso(),
            "equity": round(equity, 4),
            "cash": round(cash, 4),
            "return_pct": round(100.0 * (equity / start - 1.0), 4),
            "benchmark_hold_btc_equity": round(hold_btc, 4),
            "benchmark_hold_btc_return_pct": round(100.0 * (hold_btc / start - 1.0), 4),
            "benchmark_hold_cash_equity": round(hold_cash, 4),
            "benchmark_hold_cash_return_pct": 0.0,
            "positions": detail,
            "price_source": price_source,
            "is_live_market_data": is_live,
            "disclaimer": (
                "Paper results only. Not expected future profit. "
                "No live orders, wallets, or exchange trading keys used."
            ),
        }

    def performance_report(self) -> dict[str, Any]:
        # Official performance uses live-market-data snapshots only so mock/fallback
        # prices cannot contaminate readiness metrics.
        live_rows = self._conn.execute(
            """
            SELECT timestamp, equity FROM snapshots
            WHERE is_live_market_data=1
            ORDER BY id ASC
            """
        ).fetchall()
        all_rows = self._conn.execute(
            "SELECT timestamp, equity, is_live_market_data, price_source FROM snapshots ORDER BY id ASC"
        ).fetchall()
        mock_rows = [r for r in all_rows if not int(r["is_live_market_data"] or 0)]
        trades = self._conn.execute("SELECT COUNT(*) AS c FROM trades").fetchone()["c"]
        live_trades = self._conn.execute(
            "SELECT COUNT(*) AS c FROM trades WHERE is_live_market_data=1"
        ).fetchone()["c"]
        mock_trades = self._conn.execute(
            "SELECT COUNT(*) AS c FROM trades WHERE is_live_market_data=0"
        ).fetchone()["c"]

        def _metrics(rows: list) -> dict[str, Any]:
            if len(rows) < 2:
                return {
                    "snapshots": len(rows),
                    "max_drawdown_pct": 0.0,
                    "volatility_pct": 0.0,
                }
            equities = [float(r["equity"]) for r in rows]
            peak = equities[0]
            max_dd = 0.0
            for e in equities:
                peak = max(peak, e)
                dd = (peak - e) / peak if peak else 0.0
                max_dd = max(max_dd, dd)
            rets = []
            for i in range(1, len(equities)):
                if equities[i - 1] > 0:
                    rets.append(equities[i] / equities[i - 1] - 1.0)
            vol = (
                (math.sqrt(sum(r * r for r in rets) / len(rets)) * 100.0) if rets else 0.0
            )
            return {
                "snapshots": len(rows),
                "max_drawdown_pct": round(max_dd * 100.0, 4),
                "volatility_pct": round(vol, 4),
            }

        live_metrics = _metrics(live_rows)
        mock_metrics = _metrics(mock_rows)
        sells = self._conn.execute(
            "SELECT note FROM trades WHERE side='sell'"
        ).fetchall()
        wins = sum(1 for s in sells if "win" in (s["note"] or ""))
        win_rate = (wins / len(sells)) if sells else None

        started = datetime.fromisoformat(self._get_meta("initialized") or utc_now_iso())
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        days = max(1, (utc_now() - started).days)
        latest = self.mark_to_market()
        # Readiness only counts calendar days when live market data was used.
        live_days = live_metrics["snapshots"]  # coarse proxy until daily rollup exists
        return {
            "days_sampled": days,
            "snapshots": len(all_rows),
            "trades": trades,
            "latest": latest,
            "max_drawdown_pct": live_metrics["max_drawdown_pct"],
            "volatility_pct": live_metrics["volatility_pct"],
            "win_rate": win_rate,
            "ready_for_live_proposal": days >= 30 and live_metrics["snapshots"] >= 30,
            "min_days_required": 30,
            "disclaimer": latest["disclaimer"],
            "market_data_separation": {
                "live": {
                    **live_metrics,
                    "trades": live_trades,
                    "approx_live_marks": live_days,
                },
                "mock_or_fallback": {
                    **mock_metrics,
                    "trades": mock_trades,
                    "excluded_from_official_performance": True,
                },
            },
        }

    def run_starter_strategy_once(self) -> dict[str, Any]:
        """Simple deterministic allocation: 50% BTC / 30% ETH / 20% cash target.

        Used to generate sample paper activity without live risk.
        """
        px = self.prices.get_prices()
        equity_before = self.mark_to_market()["equity"]
        target_btc = 0.50 * equity_before / px["BTC"].usd
        target_eth = 0.30 * equity_before / px["ETH"].usd
        actions = []
        for asset, target in (("BTC", target_btc), ("ETH", target_eth)):
            delta = target - self._qty(asset)
            if abs(delta) * px[asset].usd < 1.0:
                continue
            side: Side = "buy" if delta > 0 else "sell"
            try:
                actions.append(
                    self.simulate_trade(
                        asset=asset, side=side, qty=abs(delta), note="rebalance"
                    )
                )
            except PaperTradingError as exc:
                actions.append({"asset": asset, "skipped": str(exc)})
        return {"actions": actions, "mark": self.mark_to_market()}
