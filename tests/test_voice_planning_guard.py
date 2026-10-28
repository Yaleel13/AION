from __future__ import annotations

from aion import local_voice_turn


def test_next_work_question_uses_grounded_fast_path(monkeypatch):
    monkeypatch.setenv("AION_RUNTIME_MODE", "local")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("planning guard must not call Ollama")

    monkeypatch.setattr(local_voice_turn, "urlopen", fail_urlopen)

    result = local_voice_turn.reason_locally("Hey AION, what projects should we work on next?", [])

    assert result["ok"] is True
    assert result["model"] == "aion-local-planning-guard"
    assert "haven't inspected" in result["reply"].lower()
    assert "controlled actions" in result["reply"].lower()
    assert result["network_required"] is False


def test_truth_guard_catches_fabricated_work_history():
    reply, triggered = local_voice_turn._apply_truth_guard(
        'We have been working on the "Elder Scrolls" project, and our current task is data analysis.'
    )

    assert triggered is True
    assert reply == local_voice_turn.TRUTH_GUARD_REPLY


def test_short_voice_prompt_preserves_grounding_contract():
    prompt = local_voice_turn.VOICE_SYSTEM_PROMPT

    assert len(prompt.split()) < 60
    assert "Never invent live state" in prompt
    assert "tool result" in prompt
