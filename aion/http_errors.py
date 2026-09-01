"""Safe HTTP error mapping for FastAPI handlers."""

from __future__ import annotations

import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def upstream_provider_error(exc: Exception) -> HTTPException:
    logger.exception("Upstream provider request failed", exc_info=exc)
    return HTTPException(status_code=502, detail="Upstream provider request failed")


def owner_request_error(exc: Exception, *, fallback: str = "Request could not be completed") -> HTTPException:
    logger.exception("Owner request failed", exc_info=exc)
    return HTTPException(status_code=400, detail=fallback)
