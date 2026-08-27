"""Solve Moltbook AI verification challenges (obfuscated math word problems)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from aion.moltbook.errors import MoltbookError
from aion.moltbook.redact import redact_text

_NUMBER_WORDS: list[tuple[str, float]] = [
    ("ninety", 90),
    ("eighty", 80),
    ("seventy", 70),
    ("sixty", 60),
    ("fifty", 50),
    ("forty", 40),
    ("thirty", 30),
    ("twenty", 20),
    ("nineteen", 19),
    ("eighteen", 18),
    ("seventeen", 17),
    ("sixteen", 16),
    ("fifteen", 15),
    ("fourteen", 14),
    ("thirteen", 13),
    ("twelve", 12),
    ("eleven", 11),
    ("hundred", 100),
    ("ten", 10),
    ("nine", 9),
    ("eight", 8),
    ("seven", 7),
    ("six", 6),
    ("five", 5),
    ("four", 4),
    ("three", 3),
    ("two", 2),
    ("one", 1),
    ("zero", 0),
]


def deobfuscate_challenge(text: str) -> str:
    """Strip scattered symbols; keep letters/spaces; lowercase."""
    cleaned = re.sub(r"[^A-Za-z\s]", "", text or "")
    return re.sub(r"\s+", " ", cleaned).lower().strip()


def _word_pattern(word: str) -> str:
    return "".join(f"{re.escape(ch)}+" for ch in word)


def _token_value(token: str) -> float | None:
    for word, value in _NUMBER_WORDS:
        if re.fullmatch(_word_pattern(word), token):
            return float(value)
    # Concatenated compounds: "twentythree" → 23, "fiftyone" → 51
    for tens_word, tens in _NUMBER_WORDS:
        if tens < 20 or tens % 10 != 0 or tens >= 100:
            continue
        tens_pat = _word_pattern(tens_word)
        m = re.fullmatch(rf"({tens_pat})(.+)", token)
        if not m:
            continue
        ones = _token_value(m.group(2))
        if ones is not None and 0 < ones < 10:
            return float(tens + ones)
    return None


def _pair_value(a: str, b: str) -> float | None:
    """Match number words split across adjacent tokens (twen + ty, sevent + een)."""
    joined = a + b
    for word, value in _NUMBER_WORDS:
        if re.fullmatch(_word_pattern(word), joined):
            return float(value)
    return None


def _extract_numbers(text: str) -> list[float]:
    tokens = [t for t in text.split() if t]
    numbers: list[float] = []
    i = 0
    while i < len(tokens):
        # Prefer two-token number words first.
        if i + 1 < len(tokens):
            paired = _pair_value(tokens[i], tokens[i + 1])
            if paired is not None:
                # Optional ones digit after a tens word.
                if (
                    paired >= 20
                    and paired % 10 == 0
                    and i + 2 < len(tokens)
                ):
                    ones = _token_value(tokens[i + 2])
                    if ones is not None and ones < 10:
                        numbers.append(paired + ones)
                        i += 3
                        continue
                numbers.append(paired)
                i += 2
                continue
        single = _token_value(tokens[i])
        if single is not None:
            if (
                single >= 20
                and single % 10 == 0
                and i + 1 < len(tokens)
            ):
                ones = _token_value(tokens[i + 1])
                if ones is not None and ones < 10:
                    numbers.append(single + ones)
                    i += 2
                    continue
            numbers.append(single)
        i += 1
    return numbers


def solve_challenge_text(challenge_text: str) -> str:
    """Deterministic solver; return answer formatted to 2 decimal places."""
    text = deobfuscate_challenge(challenge_text)
    numbers = _extract_numbers(text)
    # Elongated filler like "loooo oone" can inject a spurious 1.0; drop it when
    # a clear two-operand force/total problem remains.
    if (
        len(numbers) == 3
        and 1.0 in numbers
        and re.search(r"\b(total|sum|combined|force|neutrons?|plus|and)\b", text)
    ):
        numbers = [n for n in numbers if n != 1.0]
    if len(numbers) != 2:
        raise MoltbookError(
            redact_text(
                f"Ambiguous number parse ({numbers}) from challenge: {text[:160]}"
            )
        )

    a, b = numbers[0], numbers[1]
    if re.search(r"\b(times|multipl(?:y|ies|ied)|product of)\b", text):
        result = a * b
    elif re.search(r"\b(divided by|divide[sd]?|over)\b", text):
        if b == 0:
            raise MoltbookError("Challenge divide-by-zero")
        result = a / b
    elif re.search(
        r"\b(slows? by|slower by|minus|subtract(?:s|ed)?|less|loses?|"
        r"decreas(?:e|es|ed)|difference)\b",
        text,
    ):
        result = a - b
    elif re.search(
        r"\b(plus|add(?:s|ed)?|gains?|faster by|increas(?:e|es|ed)|more|"
        r"total|sum|combined|altogether|together)\b",
        text,
    ):
        result = a + b
    elif re.search(r"\band\b", text) and re.search(
        r"\b(force|total|neutrons?|meters?|shells?|claws?|adds?|drag|factor)\b",
        text,
    ):
        # "force of X and ... factor of Y multiplied" handled by multiply branch first.
        result = a + b
    else:
        result = a - b

    return f"{result:.2f}"


def solve_challenge(challenge_text: str) -> str:
    return solve_challenge_text(challenge_text)


async def verify_content(
    *,
    base_url: str,
    headers: dict[str, str],
    verification: dict[str, Any],
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Solve challenge and POST /verify. Raises on failure."""
    code = verification.get("verification_code")
    challenge = verification.get("challenge_text") or ""
    if not code or not challenge:
        raise MoltbookError("Missing verification challenge fields")
    answer = solve_challenge(challenge)
    async with httpx.AsyncClient(timeout=timeout) as http:
        resp = await http.post(
            f"{base_url}/verify",
            headers=headers,
            json={"verification_code": code, "answer": answer},
        )
    body = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not body.get("success"):
        raise MoltbookError(
            redact_text(
                f"verification failed {resp.status_code}: {str(body)[:240]} "
                f"(answer={answer}; challenge={deobfuscate_challenge(challenge)[:120]})"
            )
        )
    return {"answer": answer, "verify_response": body}
