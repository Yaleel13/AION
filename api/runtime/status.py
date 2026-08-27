"""Serverless runtime-status endpoint for Vercel."""

from fastapi import FastAPI

from aion.runtime_status import build_runtime_status

app = FastAPI()


@app.get("/api/runtime/status")
async def status() -> dict:
    return build_runtime_status()
