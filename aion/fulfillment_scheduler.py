"""Automatic fulfillment scheduler using APScheduler.

Provides flexible scheduling for order fulfillment with fail-closed defaults.
All scheduling is disabled by default and requires explicit configuration.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from aion.fulfillment import fulfill_paid_orders
from aion.opportunity_store import OpportunityStore

logger = logging.getLogger(__name__)


class FulfillmentScheduler:
    """Background scheduler for automated payment fulfillment.

    By default this scheduler is inactive. The owner must explicitly enable
    scheduled fulfillment via FULFILLMENT_SCHEDULER_ENABLED environment variable.
    """

    def __init__(self) -> None:
        self.enabled = _env_truthy("FULFILLMENT_SCHEDULER_ENABLED")
        self.interval_minutes = int(os.getenv("FULFILLMENT_SCHEDULER_INTERVAL_MINUTES") or "60")
        self.scheduler: BackgroundScheduler | None = None
        self.is_running = False

    def _fulfill_job(self) -> None:
        """Background job that processes paid orders."""
        try:
            store = OpportunityStore()
            results = fulfill_paid_orders(store)
            logger.info(f"Scheduled fulfillment completed: {len(results)} orders processed")
        except Exception as exc:
            logger.error(f"Scheduled fulfillment failed: {exc}")

    def start(self) -> dict[str, Any]:
        """Start the fulfillment scheduler.

        Returns dict with status and configuration.
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "reason": "FULFILLMENT_SCHEDULER_ENABLED not set",
            }

        if self.is_running:
            return {
                "status": "already_running",
                "interval_minutes": self.interval_minutes,
            }

        try:
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_job(
                self._fulfill_job,
                "interval",
                minutes=self.interval_minutes,
                id="fulfillment_job",
                replace_existing=True,
            )
            self.scheduler.start()
            self.is_running = True

            logger.info(
                f"Fulfillment scheduler started: {self.interval_minutes} minute interval"
            )
            return {
                "status": "started",
                "interval_minutes": self.interval_minutes,
                "note": "Scheduler running in background; processes paid orders periodically",
            }
        except Exception as exc:
            logger.error(f"Failed to start fulfillment scheduler: {exc}")
            return {
                "status": "error",
                "error": str(exc),
            }

    def stop(self) -> dict[str, Any]:
        """Stop the fulfillment scheduler.

        Returns dict with status.
        """
        if not self.is_running or not self.scheduler:
            return {
                "status": "not_running",
                "reason": "Scheduler was not started",
            }

        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Fulfillment scheduler stopped")
            return {
                "status": "stopped",
                "note": "Scheduler has been shut down; manual fulfillment can still be triggered",
            }
        except Exception as exc:
            logger.error(f"Error stopping fulfillment scheduler: {exc}")
            return {
                "status": "error",
                "error": str(exc),
            }

    def status(self) -> dict[str, Any]:
        """Get current scheduler status.

        Returns dict with running status and configuration.
        """
        return {
            "enabled": self.enabled,
            "running": self.is_running,
            "interval_minutes": self.interval_minutes if self.is_running else None,
            "configuration": {
                "FULFILLMENT_SCHEDULER_ENABLED": os.getenv("FULFILLMENT_SCHEDULER_ENABLED", ""),
                "FULFILLMENT_SCHEDULER_INTERVAL_MINUTES": os.getenv(
                    "FULFILLMENT_SCHEDULER_INTERVAL_MINUTES", "60"
                ),
            },
        }


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


# Global scheduler instance
_scheduler_instance: FulfillmentScheduler | None = None


def get_scheduler() -> FulfillmentScheduler:
    """Get or create global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = FulfillmentScheduler()
    return _scheduler_instance


def reset_scheduler() -> None:
    """Reset scheduler instance (for testing)."""
    global _scheduler_instance
    if _scheduler_instance and _scheduler_instance.is_running:
        _scheduler_instance.stop()
    _scheduler_instance = None
