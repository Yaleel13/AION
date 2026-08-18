"""FastAPI application – entry point for the AION server."""

from fastapi import FastAPI, HTTPException

from aion import config
from aion.agent_runtime import run_aion
from aion.schemas import (
    AIResponse,
    AgentRequest,
    AgentResponse,
    ChatGPTRequest,
    GeminiRequest,
)
from aion.services import query_chatgpt, query_gemini

app = FastAPI(
    title="AION",
    description="The Alchemical Intelligence for Ontological Navigation.",
    version="0.2.0",
)


@app.get("/health")
async def health() -> dict:
    """Health-check endpoint."""
    return {
        "status": "ok",
        "runtime": "agent-v1",
        "openai_configured": bool(config.OPENAI_API_KEY),
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
