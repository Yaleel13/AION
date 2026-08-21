"""Pydantic schemas for request and response payloads."""

from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Payload sent to the primary AION agent runtime."""

    message: str = Field(..., min_length=1, description="User request for AION")
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        min_length=1,
        description="Conversation/session identifier used for continuity",
    )


class AgentUsage(BaseModel):
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AgentResponse(BaseModel):
    agent: str
    session_id: str
    response: str
    requires_approval: bool = False
    usage: AgentUsage


class ChatGPTRequest(BaseModel):
    """Legacy payload sent to the ChatGPT endpoint."""

    message: str = Field(..., description="User message to send to ChatGPT")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    system_prompt: Optional[str] = Field(
        default=None, description="Optional system prompt"
    )


class GeminiRequest(BaseModel):
    """Legacy payload sent to the Gemini endpoint."""

    message: str = Field(..., description="User message to send to Gemini")
    model: str = Field(
        default="gemini-1.5-flash", description="Gemini model to use"
    )


class AIResponse(BaseModel):
    """Unified response returned by legacy provider endpoints."""

    provider: str = Field(..., description="AI provider name")
    model: str = Field(..., description="Model used")
    message: str = Field(..., description="Original user message")
    response: str = Field(..., description="AI-generated response text")
