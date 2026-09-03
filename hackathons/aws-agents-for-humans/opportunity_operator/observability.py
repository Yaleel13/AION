from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger("opportunity_operator")


def configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")


def emit_event(event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    LOGGER.info(json.dumps(payload, sort_keys=True, default=str))
