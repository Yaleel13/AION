"""Non-destructive SQLite migration into durable paths.

Preserves quota counters, risk_state (including experiment start and
quota_profile), leads, audits, paper history, and activation artifacts.
Never resets counters.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aion.durable.paths import DurablePaths, resolve_durable_paths
from aion.moltbook.security import utc_now_iso


# Known ephemeral locations used during the live experiment.
LEGACY_PHASE2_CANDIDATES = (
    "/tmp/aion_phase2_live_experiment.db",
    "/tmp/aion_phase2.db",
)
LEGACY_PAPER_CANDIDATES = ("/tmp/aion_paper_trading.db",)
LEGACY_SESSION_CANDIDATES = ("/tmp/aion_sessions.db",)
LEGACY_ACTIVATION_CANDIDATES = (
    "/tmp/aion_activation",
    "/tmp/aion_activation_final",
)

PHASE2_TABLES = (
    "approvals",
    "audit_events",
    "leads",
    "drafts",
    "risk_state",
    "autonomy_quota_events",
    "autonomy_blocks",
    "autonomy_actions",
    "autonomy_account_interactions",
    "autonomy_rate_limits",
    "daily_reports",
    "lead_alerts",
    "scheduler_state",
    "scheduler_locks",
    "health_alerts",
)

PAPER_TABLES = ("meta", "positions", "trades", "snapshots")


@dataclass
class MigrationReport:
    started_at: str
    finished_at: str | None = None
    destination: str = ""
    phase2_source: str | None = None
    paper_source: str | None = None
    session_source: str | None = None
    activation_source: str | None = None
    phase2_row_counts: dict[str, int] = field(default_factory=dict)
    paper_row_counts: dict[str, int] = field(default_factory=dict)
    quota_counts: dict[str, int] = field(default_factory=dict)
    risk_keys: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rollback_backup: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "destination": self.destination,
            "phase2_source": self.phase2_source,
            "paper_source": self.paper_source,
            "session_source": self.session_source,
            "activation_source": self.activation_source,
            "phase2_row_counts": self.phase2_row_counts,
            "paper_row_counts": self.paper_row_counts,
            "quota_counts": self.quota_counts,
            "risk_keys": self.risk_keys,
            "actions": self.actions,
            "warnings": self.warnings,
            "rollback_backup": self.rollback_backup,
        }


def _first_existing(candidates: tuple[str, ...]) -> Path | None:
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    return None


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
        return int(row[0])
    except sqlite3.Error:
        return 0


def _copy_db_file(src: Path, dest: Path, *, report: MigrationReport, label: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        src_size = src.stat().st_size
        dest_size = dest.stat().st_size
        dest_incomplete = False
        if label == "phase2" and dest_size > 0:
            try:
                conn = sqlite3.connect(str(dest))
                tables = {
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                conn.close()
                required = {"autonomy_quota_events", "risk_state", "audit_events"}
                dest_incomplete = not required.issubset(tables)
            except sqlite3.Error:
                dest_incomplete = True
        if dest_size > 0 and dest_size >= src_size and not dest_incomplete:
            report.warnings.append(
                f"{label}: destination already present and not smaller than source; "
                "left unchanged to avoid resetting state"
            )
            report.actions.append(f"skip_copy:{label}")
            return
        if dest_incomplete:
            report.actions.append(f"replace_incomplete_dest:{label}")
        backup = dest.with_suffix(dest.suffix + f".bak.{utc_now_iso().replace(':', '-')}")
        shutil.copy2(dest, backup)
        report.actions.append(f"backup_dest:{label}:{backup}")
    shutil.copy2(src, dest)
    report.actions.append(f"copied:{label}:{src}->{dest}")


def _verify_phase2(path: Path, report: MigrationReport) -> None:
    conn = sqlite3.connect(str(path))
    try:
        for table in PHASE2_TABLES:
            report.phase2_row_counts[table] = _table_count(conn, table)
        rows = conn.execute(
            "SELECT action, COUNT(*) FROM autonomy_quota_events GROUP BY action"
        ).fetchall()
        report.quota_counts = {str(a): int(c) for a, c in rows}
        keys = conn.execute("SELECT key FROM risk_state ORDER BY key").fetchall()
        report.risk_keys = [str(r[0]) for r in keys]
    except sqlite3.Error as exc:
        report.warnings.append(f"phase2_verify:{exc}")
    finally:
        conn.close()


def _verify_paper(path: Path, report: MigrationReport) -> None:
    if not path.exists():
        return
    conn = sqlite3.connect(str(path))
    try:
        for table in PAPER_TABLES:
            report.paper_row_counts[table] = _table_count(conn, table)
    except sqlite3.Error as exc:
        report.warnings.append(f"paper_verify:{exc}")
    finally:
        conn.close()


def migrate_to_durable(
    *,
    paths: DurablePaths | None = None,
    phase2_source: str | Path | None = None,
    paper_source: str | Path | None = None,
    session_source: str | Path | None = None,
    activation_source: str | Path | None = None,
    dry_run: bool = False,
) -> MigrationReport:
    """Copy legacy /tmp SQLite + activation into durable locations.

    Idempotent: will not overwrite a destination that already holds equal-or-larger data.
    """
    report = MigrationReport(started_at=utc_now_iso())
    dest = paths or resolve_durable_paths()
    dest.ensure()
    report.destination = str(dest.root)

    p2_src = Path(phase2_source) if phase2_source else _first_existing(LEGACY_PHASE2_CANDIDATES)
    paper_src = Path(paper_source) if paper_source else _first_existing(LEGACY_PAPER_CANDIDATES)
    sess_src = Path(session_source) if session_source else _first_existing(LEGACY_SESSION_CANDIDATES)
    act_src = (
        Path(activation_source)
        if activation_source
        else _first_existing(LEGACY_ACTIVATION_CANDIDATES)
    )

    if dry_run:
        report.phase2_source = str(p2_src) if p2_src else None
        report.paper_source = str(paper_src) if paper_src else None
        report.session_source = str(sess_src) if sess_src else None
        report.activation_source = str(act_src) if act_src else None
        report.actions.append("dry_run")
        report.finished_at = utc_now_iso()
        return report

    backup_root = dest.root / "migration_backups" / utc_now_iso().replace(":", "-")
    backup_root.mkdir(parents=True, exist_ok=True)
    report.rollback_backup = str(backup_root)

    if p2_src and p2_src.exists():
        report.phase2_source = str(p2_src)
        if dest.phase2_db.exists():
            shutil.copy2(dest.phase2_db, backup_root / "phase2_before.db")
        _copy_db_file(p2_src, dest.phase2_db, report=report, label="phase2")
        _verify_phase2(dest.phase2_db, report)
    else:
        report.warnings.append("no_phase2_source_found")

    if paper_src and paper_src.exists():
        report.paper_source = str(paper_src)
        if dest.paper_db.exists():
            shutil.copy2(dest.paper_db, backup_root / "paper_before.db")
        _copy_db_file(paper_src, dest.paper_db, report=report, label="paper")
        _verify_paper(dest.paper_db, report)
    else:
        report.warnings.append("no_paper_source_found")

    if sess_src and sess_src.exists():
        report.session_source = str(sess_src)
        _copy_db_file(sess_src, dest.session_db, report=report, label="session")

    if act_src and act_src.exists():
        report.activation_source = str(act_src)
        dest.activation_dir.mkdir(parents=True, exist_ok=True)
        if act_src.is_dir():
            for item in act_src.iterdir():
                target = dest.activation_dir / item.name
                if item.is_file():
                    shutil.copy2(item, target)
                    report.actions.append(f"copied_activation_file:{item.name}")
        report.actions.append(f"activation_dir:{dest.activation_dir}")

    # Write migration receipt for rollback documentation.
    receipt = dest.root / "last_migration.json"
    report.finished_at = utc_now_iso()
    receipt.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    report.actions.append(f"receipt:{receipt}")
    return report


def rollback_from_backup(backup_dir: str | Path, paths: DurablePaths | None = None) -> dict[str, Any]:
    """Restore phase2/paper DBs from a migration_backups folder."""
    backup = Path(backup_dir)
    dest = paths or resolve_durable_paths()
    actions: list[str] = []
    p2 = backup / "phase2_before.db"
    paper = backup / "paper_before.db"
    if p2.exists():
        shutil.copy2(p2, dest.phase2_db)
        actions.append(f"restored_phase2:{p2}")
    if paper.exists():
        shutil.copy2(paper, dest.paper_db)
        actions.append(f"restored_paper:{paper}")
    return {
        "rolled_back_at": utc_now_iso(),
        "backup_dir": str(backup),
        "actions": actions,
    }
