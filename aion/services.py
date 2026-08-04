"""Service layer for interacting with ChatGPT (OpenAI) and Gemini APIs."""

from openai import AsyncOpenAI
from google import genai
from google.genai import types as genai_types

from aion import config
from aion.schemas import AIResponse, ChatGPTRequest, GeminiRequest


async def query_chatgpt(request: ChatGPTRequest) -> AIResponse:
    """Send a message to ChatGPT and return the response."""
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})

    completion = await client.chat.completions.create(
        model=request.model,
        messages=messages,
    )

    response_text = completion.choices[0].message.content or ""
    return AIResponse(
        provider="chatgpt",
        model=request.model,
        message=request.message,
        response=response_text,
    )


async def query_gemini(request: GeminiRequest) -> AIResponse:
    """Send a message to Gemini and return the response."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    result = await client.aio.models.generate_content(
        model=request.model,
        contents=request.message,
        config=genai_types.GenerateContentConfig(),
    )
    response_text = result.text or ""

    return AIResponse(
        provider="gemini",
        model=request.model,
        message=request.message,
        response=response_text,
    )
