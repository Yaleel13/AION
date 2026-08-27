"""Regression: private founder charter must never enter public agent instructions."""

from __future__ import annotations

import aion.agent_runtime as runtime


def test_private_owner_context_not_in_public_instructions(tmp_path, monkeypatch) -> None:
    # Synthetic secret — do not paste real founder charter text into the repo.
    secret = "SYNTHETIC_OWNER_CHARTER_TOKEN_DO_NOT_PUBLISH_9f3c2a"
    path = tmp_path / "OWNER_PRIVATE_CONTEXT.md"
    path.write_text(f"Private charter line: {secret}", encoding="utf-8")
    monkeypatch.setattr(runtime, "_PRIVATE_CONTEXT_PATH", path)

    assert runtime.private_owner_context_exists() is True
    assert secret not in runtime.AION_INSTRUCTIONS
    assert "SYNTHETIC_OWNER_CHARTER_TOKEN" not in runtime.AION_INSTRUCTIONS
    source = open(runtime.__file__, encoding="utf-8").read()
    assert secret not in source
