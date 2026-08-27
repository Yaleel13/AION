"""FastAPI application – entry point for the AION server."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from aion import config
from aion.agent_runtime import run_aion
from aion.moltbook.errors import MoltbookConfigError
from aion.moltbook.settings import load_moltbook_settings
from aion.schemas import (
    AIResponse,
    AgentRequest,
    AgentResponse,
    ChatGPTRequest,
    GeminiRequest,
)
from aion.services import query_chatgpt, query_gemini


def _moltbook_health() -> dict:
    """Report Moltbook integration status without exposing secrets."""
    try:
        settings = load_moltbook_settings()
    except MoltbookConfigError as exc:
        return {
            "configured": False,
            "mode": None,
            "outbound_enabled": False,
            "phase": "phase1-readonly",
            "error": str(exc),
        }
    return {
        "configured": settings.is_mock or settings.configured_for_live,
        "mode": settings.mode,
        "api_key_present": bool(settings.api_key),
        "outbound_enabled": False,
        "phase": "phase1-readonly",
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate optional Moltbook settings without failing closed on misconfig."""
    try:
        load_moltbook_settings()
    except MoltbookConfigError:
        # Live callers fail closed on client create; health surfaces the error.
        pass
    yield


app = FastAPI(
    title="AION",
    description="The Alchemical Intelligence for Ontological Navigation.",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    """Health-check endpoint."""
    return {
        "status": "ok",
        "runtime": "agent-v1",
        "openai_configured": bool(config.OPENAI_API_KEY),
        "moltbook": _moltbook_health(),
    }


@app.post("/agent", response_model=AgentResponse, summary="Run AION")
async def agent_endpoint(request: AgentRequest) -> AgentResponse:
    """Run one turn through the primary AION agent orchestrator."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        result = await run_aion(request.message, request.session_id)
        return AgentResponse.model_validate(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/chatgpt", response_model=AIResponse, summary="Query ChatGPT (legacy)")
async def chatgpt_endpoint(request: ChatGPTRequest) -> AIResponse:
    """Forward a message to OpenAI ChatGPT and return the response."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        return await query_chatgpt(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/gemini", response_model=AIResponse, summary="Query Gemini (legacy)")
async def gemini_endpoint(request: GeminiRequest) -> AIResponse:
    """Forward a message to Google Gemini and return the response."""
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    try:
        return await query_gemini(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
