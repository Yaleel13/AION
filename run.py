"""Entry-point script to run the AION local server."""

import os

import uvicorn
from fastapi import HTTPException, Request

from aion import config
from aion.local_memory import LocalMemoryRequest, handle_local_memory
from aion.main import app


@app.post("/local-memory", summary="Local durable conversation memory")
async def local_memory_endpoint(
    body: LocalMemoryRequest,
    http_request: Request,
) -> dict:
    """Serve local SQLite conversation memory to loopback callers only."""
    client_host = http_request.client.host if http_request.client else None
    if client_host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="Local memory is loopback-only")

    if (os.getenv("AION_RUNTIME_MODE") or "").strip().lower() != "local":
        raise HTTPException(status_code=503, detail="Local memory is not enabled")

    try:
        return handle_local_memory(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - fail closed without leaking storage details
        raise HTTPException(status_code=500, detail="Local memory operation failed") from exc


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=True,
    )
