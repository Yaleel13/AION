"""Pydantic schemas for request and response payloads."""

from pydantic import BaseModel, Field
from typing import Optional


class ChatGPTRequest(BaseModel):
    """Payload sent to the ChatGPT endpoint."""

    message: str = Field(..., description="User message to send to ChatGPT")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    system_prompt: Optional[str] = Field(
        default=None, description="Optional system prompt"
    )


class GeminiRequest(BaseModel):
    """Payload sent to the Gemini endpoint."""

    message: str = Field(..., description="User message to send to Gemini")
    model: str = Field(
        default="gemini-1.5-flash", description="Gemini model to use"
    )


class AIResponse(BaseModel):
    """Unified response returned by all AI endpoints."""

    provider: str = Field(..., description="AI provider name")
    model: str = Field(..., description="Model used")
    message: str = Field(..., description="Original user message")
    response: str = Field(..., description="AI-generated response text")
