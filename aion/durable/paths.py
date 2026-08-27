"""Resolve durable on-disk paths. Prefer AION_DATA_DIR over ephemeral /tmp."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Repo-local durable default (gitignored). Survives process restart on a
# persistent volume; for managed durability set AION_DATABASE_URL (Postgres)
# or mount AION_DATA_DIR on durable disk.
DEFAULT_DATA_DIR = "data/aion"
VERCEL_TEMP_DATA_DIR = "/tmp/aion"


@dataclass(frozen=True, slots=True)
class DurablePaths:
    root: Path
    phase2_db: Path
    paper_db: Path
    session_db: Path
    activation_dir: Path
    scheduler_dir: Path

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.activation_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler_dir.mkdir(parents=True, exist_ok=True)


def resolve_durable_paths(
    environ: dict[str, str] | None = None,
) -> DurablePaths:
    env = environ if environ is not None else dict(os.environ)

    configured_root = env.get("AION_DATA_DIR")
    if configured_root:
        root = Path(configured_root).expanduser()
    elif env.get("VERCEL"):
        # Vercel's deployed source tree under /var/task is read-only. Postgres is
        # the durable production backend, so unavoidable local compatibility
        # state must use the writable but explicitly ephemeral /tmp filesystem.
        root = Path(VERCEL_TEMP_DATA_DIR)
    else:
        root = Path(DEFAULT_DATA_DIR)

    if not root.is_absolute():
        # Resolve relative to process CWD (typically repo root).
        root = Path.cwd() / root

    phase2 = env.get("AION_PHASE2_DB") or str(root / "phase2.db")
    paper = env.get("AION_PAPER_DB") or str(root / "paper_trading.db")
    session = env.get("AION_SESSION_DB") or str(root / "sessions.db")
    activation = env.get("AION_ACTIVATION_DIR") or str(root / "activation")
    scheduler = env.get("AION_SCHEDULER_DIR") or str(root / "scheduler")

    paths = DurablePaths(
        root=root,
        phase2_db=Path(phase2),
        paper_db=Path(paper),
        session_db=Path(session),
        activation_dir=Path(activation),
        scheduler_dir=Path(scheduler),
    )
    paths.ensure()
    return paths
