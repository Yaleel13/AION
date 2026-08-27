"""OpenAI guard: allowlist, ceilings, scrubbing, fallback."""

from __future__ import annotations

from aion.llm.openai_guard import (
    GuardedResult,
    OpenAIGuard,
    OpenAIGuardConfig,
    OpenAIUsageStore,
)


def test_blocks_secret_material(tmp_path):
    guard = OpenAIGuard(
        config=OpenAIGuardConfig(
            allowlist=("gpt-4o-mini",),
            max_input_tokens=1000,
            max_output_tokens=200,
            daily_cost_usd=5.0,
            timeout_seconds=10,
            max_retries=1,
            default_model="gpt-4o-mini",
        ),
        usage=OpenAIUsageStore(str(tmp_path / "u.db")),
    )
    result = guard.prepare(
        message="here is key sk-abcdefghijklmnopqrstuvwxyz",
        system_prompt=None,
        model="gpt-4o-mini",
    )
    assert isinstance(result, GuardedResult)
    assert result.fallback is True
    assert "secret_material" in result.reasons


def test_rejects_non_allowlisted_model(tmp_path):
    guard = OpenAIGuard(
        config=OpenAIGuardConfig(
            allowlist=("gpt-4o-mini",),
            max_input_tokens=1000,
            max_output_tokens=200,
            daily_cost_usd=5.0,
            timeout_seconds=10,
            max_retries=1,
            default_model="gpt-4o-mini",
        ),
        usage=OpenAIUsageStore(str(tmp_path / "u.db")),
    )
    try:
        guard.prepare(message="hi", system_prompt=None, model="gpt-evil")
        assert False, "expected error"
    except ValueError as exc:
        assert "model_not_allowlisted" in str(exc)


def test_daily_ceiling_triggers_fallback(tmp_path):
    usage = OpenAIUsageStore(str(tmp_path / "u.db"))
    usage.record(
        model="gpt-4o-mini",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        estimated_cost_usd=9.0,
        success=True,
        detail={},
    )
    guard = OpenAIGuard(
        config=OpenAIGuardConfig(
            allowlist=("gpt-4o-mini",),
            max_input_tokens=1000,
            max_output_tokens=200,
            daily_cost_usd=5.0,
            timeout_seconds=10,
            max_retries=1,
            default_model="gpt-4o-mini",
        ),
        usage=usage,
    )
    result = guard.prepare(message="hello", system_prompt=None, model="gpt-4o-mini")
    assert isinstance(result, GuardedResult)
    assert "daily_cost_ceiling" in result.reasons
