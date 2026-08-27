"""Service layer for interacting with ChatGPT (OpenAI) and Gemini APIs."""

from openai import AsyncOpenAI
from google import genai
from google.genai import types as genai_types

from aion import config
from aion.llm.openai_guard import GuardedRequest, GuardedResult, OpenAIGuard
from aion.schemas import AIResponse, ChatGPTRequest, GeminiRequest


async def query_chatgpt(request: ChatGPTRequest) -> AIResponse:
    """Send a message to ChatGPT under cost/safety guards."""
    guard = OpenAIGuard()
    prepared = guard.prepare(
        message=request.message,
        system_prompt=request.system_prompt,
        model=request.model,
    )
    if isinstance(prepared, GuardedResult):
        return AIResponse(
            provider="chatgpt_fallback",
            model=prepared.model,
            message=request.message,
            response=prepared.response,
        )

    assert isinstance(prepared, GuardedRequest)
    client = AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=guard.config.timeout_seconds,
        max_retries=guard.config.max_retries,
    )
    try:
        completion = await client.chat.completions.create(
            model=prepared.model,
            messages=prepared.messages,
            max_tokens=prepared.max_output_tokens,
        )
        response_text = completion.choices[0].message.content or ""
        usage = completion.usage
        in_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        out_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        guard.record_usage(
            model=prepared.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            success=True,
        )
        # Soft structured validation — plain text allowed.
        guard.validate_structured(response_text)
        return AIResponse(
            provider="chatgpt",
            model=prepared.model,
            message=request.message,
            response=response_text,
        )
    except Exception as exc:  # noqa: BLE001
        guard.record_usage(
            model=prepared.model,
            input_tokens=0,
            output_tokens=0,
            success=False,
            detail={"error": type(exc).__name__},
        )
        return AIResponse(
            provider="chatgpt_fallback",
            model=prepared.model,
            message=request.message,
            response=(
                "OpenAI request failed; AION fell back to safe non-LLM behavior. "
                "Please retry later or rephrase."
            ),
        )


async def query_gemini(request: GeminiRequest) -> AIResponse:
    """Gemini remains available but is not the configured primary provider."""
    if not (config.GEMINI_API_KEY or "").strip() or config.GEMINI_API_KEY.startswith(
        "your_"
    ):
        return AIResponse(
            provider="gemini_fallback",
            model=request.model,
            message=request.message,
            response="Gemini is not configured. Use OpenAI as the primary provider.",
        )
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
