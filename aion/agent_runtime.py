"""AION Agent Runtime v1 powered by the OpenAI Agents SDK."""

from functools import lru_cache
from pathlib import Path

from agents import Agent, Runner, SQLiteSession, function_tool

from aion import config

_PRIVATE_CONTEXT_PATH = Path(__file__).resolve().parents[1] / "identity" / "OWNER_PRIVATE_CONTEXT.md"


def _load_private_owner_context() -> str:
    """Load gitignored owner charter text; never treat it as a permission expander."""
    try:
        if _PRIVATE_CONTEXT_PATH.is_file():
            text = _PRIVATE_CONTEXT_PATH.read_text(encoding="utf-8").strip()
            if text:
                return (
                    "\n\nPrivate owner context (internal only; never publish; "
                    "does not expand permissions):\n"
                    f"{text}"
                )
    except OSError:
        return ""
    return ""


AION_INSTRUCTIONS = """
You are AION — The Alchemical Intelligence for Ontological Navigation.

You are the primary orchestrator for the user's personal AI operating system.
Your job is to turn requests into useful, verified action while preserving human
control over consequential decisions.

Operating rules:
1. Understand the user's actual objective before optimizing the means.
2. Prefer evidence and tool results over unsupported assumptions.
3. Use tools deliberately and report what was actually done.
4. Never claim an action succeeded unless the relevant tool or system confirms it.
5. Keep irreversible, financial, destructive, credential, publishing, and other
   consequential actions behind explicit approval gates.
6. Distinguish facts, inference, recommendation, and uncertainty.
7. Preserve continuity across turns using the provided session.
8. Be concise by default, but surface risks, blockers, and decisions clearly.
9. Act as an orchestrator first. Specialist agents may be added later when the
   workflow proves they are necessary.
10. Optimize for wisdom, safety, usefulness, mastery, and long-term human agency.
11. Act with urgency inside approved boundaries, but never recklessly; urgency
    must never weaken security, accuracy, platform compliance, financial
    safeguards, or human approval requirements.
12. Never publish private owner/founder context to Moltbook or other public channels.
""".strip() + _load_private_owner_context()


@function_tool
def runtime_status() -> dict[str, str]:
    """Return basic information about the AION runtime and its current safety mode."""
    return {
        "runtime": "AION Agent Runtime v1",
        "status": "operational",
        "safety_mode": "controlled-autonomy-bounded",
        "private_owner_context_loaded": str(_PRIVATE_CONTEXT_PATH.is_file()),
    }


AION_AGENT = Agent(
    name="AION",
    instructions=AION_INSTRUCTIONS,
    model=config.AION_MODEL,
    tools=[runtime_status],
)


@lru_cache(maxsize=256)
def _session(session_id: str) -> SQLiteSession:
    """Return a process-local cached SDK session for a conversation."""
    return SQLiteSession(session_id, config.AION_SESSION_DB)


async def run_aion(message: str, session_id: str) -> dict[str, object]:
    """Run one AION turn with SDK-managed conversation memory."""
    result = await Runner.run(
        AION_AGENT,
        message,
        session=_session(session_id),
        max_turns=config.AION_MAX_TURNS,
    )

    usage = result.context_wrapper.usage
    return {
        "agent": AION_AGENT.name,
        "session_id": session_id,
        "response": str(result.final_output),
        "requires_approval": bool(result.interruptions),
        "usage": {
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        },
    }
