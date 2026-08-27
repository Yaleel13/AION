"""Unit tests for Moltbook verification challenge solver."""

from aion.moltbook.verification import (
    _extract_numbers,
    deobfuscate_challenge,
    solve_challenge_text,
)


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


def test_antenna_does_not_fake_ten() -> None:
    text = deobfuscate_challenge(
        "claw force of thirty five neutrons and an antenna drag factor of two multiplied"
    )
    nums = _extract_numbers(text)
    assert 10.0 not in nums
    assert (
        solve_challenge_text(
            "claw force of thirty five neutrons and an antenna drag factor of two "
            "multiplied by what"
        )
        == "70.00"
    )


def test_solve_total_force_addition() -> None:
    raw = (
        "A] lO b.StErRr Lo^oOobssstErrr' S ClAwW ExE rTs^ tWeN tY- tHrEe] nEu.-ToNs "
        "Um, aNd] tHe^ OtHeR ClAwW ExE rTs^ sEvEnT eeN{ nEuTo.ns- wHaT] Is^ tHe ToTaL- FoRcE?"
    )
    assert solve_challenge_text(raw) == "40.00"


def test_concatenated_twentythree_five() -> None:
    raw = (
        "a looobssster swims loooong um and its claws exerts friction force so that "
        "the effective lever amp looks like twentythree five neutons eh um how much total force"
    )
    assert _extract_numbers(deobfuscate_challenge(raw)) == [23.0, 5.0]
    assert solve_challenge_text(raw) == "28.00"


def test_spurious_one_from_elongated_filler() -> None:
    raw = (
        "a lobster exe rts um twenty fivee nootons with loooo oone claw the other "
        "exe rts fifteen nootons how total force"
    )
    assert solve_challenge_text(raw) == "40.00"
