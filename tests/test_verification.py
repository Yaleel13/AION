"""Unit tests for Moltbook verification challenge solver."""

from aion.moltbook.verification import deobfuscate_challenge, solve_challenge_text


def test_deobfuscate_and_solve_example() -> None:
    raw = "A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fI[vE, wH-aTs] ThE/ nEw^ SpE[eD?"
    cleaned = deobfuscate_challenge(raw)
    assert "lobster" in cleaned
    assert "five" in cleaned
    assert solve_challenge_text(raw) == "15.00"


def test_solve_addition() -> None:
    assert solve_challenge_text("A lobster gains three shells plus seven pearls") == "10.00"


def test_solve_multiply() -> None:
    assert solve_challenge_text("Eight crabs times two waves") == "16.00"
