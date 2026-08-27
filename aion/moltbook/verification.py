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
    # Allow duplicated letters introduced by shatter obfuscation (twenntyy → twenty).
    return "".join(f"{re.escape(ch)}+" for ch in word)


def _extract_numbers(text: str) -> list[float]:
    """Find number words in order; support compounds like twenty+five."""
    compact = text.replace(" ", "")
    matches: list[tuple[int, int, float]] = []
    for word, value in _NUMBER_WORDS:
        for m in re.finditer(_word_pattern(word), compact):
            matches.append((m.start(), m.end(), float(value)))
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    # Greedy non-overlapping, preferring longer spans already via sort secondary.
    picked: list[tuple[int, int, float]] = []
    for start, end, value in matches:
        if any(not (end <= p0 or start >= p1) for p0, p1, _ in picked):
            continue
        picked.append((start, end, value))
    picked.sort(key=lambda x: x[0])

    numbers: list[float] = []
    i = 0
    while i < len(picked):
        _s, e, val = picked[i]
        # Compound tens + ones if adjacent / overlapping gap small.
        if i + 1 < len(picked) and val >= 20 and val % 10 == 0 and picked[i + 1][2] < 10:
            if picked[i + 1][0] <= e + 2:
                numbers.append(val + picked[i + 1][2])
                i += 2
                continue
        numbers.append(val)
        i += 1
    return numbers


def solve_challenge_text(challenge_text: str) -> str:
    """Return answer formatted to 2 decimal places."""
    text = deobfuscate_challenge(challenge_text)
    numbers = _extract_numbers(text)
    if len(numbers) < 2:
        raise MoltbookError(
            redact_text(f"Could not parse two numbers from challenge: {text[:120]}")
        )

    a, b = numbers[0], numbers[1]
    if re.search(r"\b(divided by|divide[sd]?|over)\b", text):
        if b == 0:
            raise MoltbookError("Challenge divide-by-zero")
        result = a / b
    elif re.search(r"\b(times|multipl(?:y|ies|ied)|product of)\b", text):
        result = a * b
    elif re.search(
        r"\b(slows? by|slower by|minus|subtract(?:s|ed)?|less|loses?|decreas(?:e|es|ed))\b",
        text,
    ):
        result = a - b
    elif re.search(
        r"\b(plus|add(?:s|ed)?|gains?|faster by|increas(?:e|es|ed)|more)\b", text
    ):
        result = a + b
    else:
        result = a - b

    return f"{result:.2f}"


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
    answer = solve_challenge_text(challenge)
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
                f"(answer={answer})"
            )
        )
    return {"answer": answer, "verify_response": body}
