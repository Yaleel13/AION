"""Durable experiment-ops scheduler: locking, health, no catch-up."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from aion.durable.scheduler_store import SchedulerStore
from aion.moltbook.security import KillSwitch, utc_now, utc_now_iso

LOCK_NAME = "experiment_ops_cycle"
DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_LOCK_TTL_SECONDS = 900
DEFAULT_MISS_AFTER_MINUTES = 150  # alert if no success ~2.5 cycles
DEFAULT_FAIL_READONLY_AFTER = 3

CycleFn = Callable[..., Awaitable[dict[str, Any]]]


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class ExperimentOpsScheduler:
    """Wraps one ops cycle with distributed locking and health rules.

    Guarantees:
    - At most one overlapping execution (DB lock)
    - Kill switch short-circuits before work
    - No catch-up batches after downtime (single cycle attempt only)
    - Repeated failures → autonomy read-only + health alert
    - Missed cycles → health alert (delivery wired by owner-alert module)
    """

    def __init__(
        self,
        scheduler: SchedulerStore,
        *,
        kill_switch: KillSwitch | None = None,
        interval_minutes: int | None = None,
        lock_ttl_seconds: int | None = None,
        miss_after_minutes: int | None = None,
        fail_readonly_after: int | None = None,
    ):
        self.scheduler = scheduler
        self.kill_switch = kill_switch or KillSwitch.from_env()
        self.interval_minutes = interval_minutes or int(
            os.getenv("AION_SCHEDULER_INTERVAL_MINUTES", str(DEFAULT_INTERVAL_MINUTES))
        )
        self.lock_ttl_seconds = lock_ttl_seconds or int(
            os.getenv("AION_SCHEDULER_LOCK_TTL_SECONDS", str(DEFAULT_LOCK_TTL_SECONDS))
        )
        self.miss_after_minutes = miss_after_minutes or int(
            os.getenv("AION_SCHEDULER_MISS_AFTER_MINUTES", str(DEFAULT_MISS_AFTER_MINUTES))
        )
        self.fail_readonly_after = fail_readonly_after or int(
            os.getenv(
                "AION_SCHEDULER_FAIL_READONLY_AFTER", str(DEFAULT_FAIL_READONLY_AFTER)
            )
        )

    def check_missed_cycle(self) -> dict[str, Any] | None:
        last = self.scheduler.get_state("last_success_at")
        last_dt = _parse_iso(last if isinstance(last, str) else None)
        now = utc_now()
        if last_dt is None:
            # First run — not a miss.
            return None
        age_min = (now - last_dt).total_seconds() / 60.0
        if age_min <= self.miss_after_minutes:
            return None
        detail = {
            "alert_type": "missed_cycle",
            "last_success_at": last,
            "age_minutes": round(age_min, 1),
            "threshold_minutes": self.miss_after_minutes,
            "message": (
                "AION experiment_ops_cycle missed its expected window. "
                "No catch-up publish batch will be run."
            ),
        }
        alert_id = self.scheduler.log_health_alert("missed_cycle", detail)
        detail["alert_id"] = alert_id
        return detail

    def _enter_readonly_on_failures(self, fails: int) -> dict[str, Any] | None:
        if fails < self.fail_readonly_after:
            return None
        # Persist read-only hint into risk_state via scheduler_state; autonomy
        # policy also honors AION_KILL_SWITCH / reduced profile. Here we set a
        # durable flag the runner checks before outbound.
        flag = {
            "engaged": True,
            "reason": f"scheduler_consecutive_failures:{fails}",
            "engaged_at": utc_now_iso(),
        }
        self.scheduler.set_state("force_readonly", flag)
        alert_id = self.scheduler.log_health_alert("force_readonly", flag)
        return {"force_readonly": flag, "alert_id": alert_id}

    async def run_once(
        self,
        cycle_fn: CycleFn,
        *,
        flush_queue: bool = False,
        publish_next_draft: bool = False,
        owner_id: str | None = None,
        allow_catch_up: bool = False,
    ) -> dict[str, Any]:
        """Run a single cycle. ``allow_catch_up`` is always forced False."""
        allow_catch_up = False  # hard rule — never publish catch-up batches
        result: dict[str, Any] = {
            "scheduler": True,
            "started_at": utc_now_iso(),
            "allow_catch_up": allow_catch_up,
            "interval_minutes": self.interval_minutes,
        }

        miss = self.check_missed_cycle()
        if miss:
            result["missed_cycle_alert"] = miss

        if self.kill_switch.engaged:
            result["success"] = True
            result["skipped"] = "kill_switch_engaged"
            result["published"] = False
            self.scheduler.record_cycle_result(result)
            return result

        force_ro = self.scheduler.get_state("force_readonly") or {}
        if isinstance(force_ro, dict) and force_ro.get("engaged"):
            # Health-only cycle: still allow lead scan/report but strip publishes.
            flush_queue = False
            publish_next_draft = False
            result["force_readonly"] = force_ro

        lock = self.scheduler.try_acquire_lock(
            LOCK_NAME,
            owner_id=owner_id or f"scheduler-{uuid4().hex[:12]}",
            ttl_seconds=self.lock_ttl_seconds,
            meta={"flush_queue": flush_queue, "publish_next_draft": publish_next_draft},
        )
        result["lock"] = {
            "acquired": lock.get("acquired"),
            "owner_id": lock.get("owner_id"),
            "reason": lock.get("reason"),
        }
        if not lock.get("acquired"):
            result["success"] = True
            result["skipped"] = "lock_held"
            result["published"] = False
            # Do not count lock contention as failure.
            return result

        owner = str(lock["owner_id"])
        try:
            # Transient-safe: one attempt; cycle_fn / HTTP client handle retries.
            cycle_result = await cycle_fn(
                flush_queue=flush_queue,
                publish_next_draft=publish_next_draft,
            )
            result["cycle"] = cycle_result
            # Treat explicit kill/stop as success skip; exceptions as failure.
            if cycle_result.get("stopped") == "kill_switch_engaged":
                result["success"] = True
                result["skipped"] = "kill_switch_engaged"
            else:
                result["success"] = "error" not in cycle_result
            result["published"] = bool(cycle_result.get("published"))
            if not result["success"]:
                result["error"] = cycle_result.get("error") or "cycle_reported_error"
        except Exception as exc:  # noqa: BLE001 — record then re-raise policy
            result["success"] = False
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["published"] = False
        finally:
            self.scheduler.release_lock(LOCK_NAME, owner)

        self.scheduler.record_cycle_result(result)
        if not result.get("success"):
            fails = int(self.scheduler.get_state("consecutive_failures", 0) or 0)
            ro = self._enter_readonly_on_failures(fails)
            if ro:
                result["readonly_engaged"] = ro
        result["finished_at"] = utc_now_iso()
        return result

    def clear_force_readonly(self, *, reason: str = "owner_clear") -> None:
        self.scheduler.set_state(
            "force_readonly",
            {"engaged": False, "cleared_at": utc_now_iso(), "reason": reason},
        )
