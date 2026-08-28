# Paper boolean Postgres compatibility

Production cron exposed a Postgres type mismatch in paper-trading writes: `aion.paper_snapshots.is_live_market_data` and `aion.paper_trades.is_live_market_data` are boolean columns, while the engine used SQLite-style `0`/`1` values and comparisons.

Required correction:
- pass Python `bool` values for `is_live_market_data` inserts;
- use SQL `TRUE`/`FALSE` predicates for boolean queries (SQLite accepts these aliases too);
- preserve paper-only behavior and all existing safety gates.
