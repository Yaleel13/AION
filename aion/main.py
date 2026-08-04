"""FastAPI application – entry point for the AION server."""

from fastapi import FastAPI, HTTPException

from aion import config
from aion.schemas import AIResponse, ChatGPTRequest, GeminiRequest
from aion.services import query_chatgpt, query_gemini

app = FastAPI(
    title="AION",
    description="Alchemical Intelligence for Ontological Navigation – receives data from ChatGPT and Gemini.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/chatgpt", response_model=AIResponse, summary="Query ChatGPT")
async def chatgpt_endpoint(request: ChatGPTRequest) -> AIResponse:
    """Forward a message to OpenAI ChatGPT and return the response."""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        return await query_chatgpt(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/gemini", response_model=AIResponse, summary="Query Gemini")
async def gemini_endpoint(request: GeminiRequest) -> AIResponse:
    """Forward a message to Google Gemini and return the response."""
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    try:
        return await query_gemini(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
