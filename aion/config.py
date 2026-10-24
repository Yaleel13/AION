"""Configuration loaded from environment variables."""

import os
from collections.abc import Mapping
from dotenv import load_dotenv

load_dotenv()


def resolve_app_host(environ: Mapping[str, str] | None = None) -> str:
    """Resolve the FastAPI bind host with a loopback-safe default.

    Local AION OS should not expose its runtime to the LAN unless the owner
    deliberately sets ``APP_HOST`` to another interface such as ``0.0.0.0``.
    """
    env = environ if environ is not None else os.environ
    value = (env.get("APP_HOST") or "").strip()
    return value or "127.0.0.1"


OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
# Legacy flat Moltbook vars kept for compatibility. Prefer
# ``aion.moltbook.load_moltbook_settings`` for validated Phase 1 config.
MOLTBOOK_API_KEY: str = os.getenv("MOLTBOOK_API_KEY", "")
MOLTBOOK_BASE_URL: str = os.getenv(
    "MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1"
)
MOLTBOOK_MODE: str = os.getenv("MOLTBOOK_MODE", "mock")
AION_MODEL: str = os.getenv("AION_MODEL", "gpt-5.4")
AION_SESSION_DB: str = os.getenv("AION_SESSION_DB", "/tmp/aion_sessions.db")
AION_MAX_TURNS: int = int(os.getenv("AION_MAX_TURNS", "8"))
AGENT_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("AGENT_RATE_LIMIT_PER_MINUTE", "30"))
APP_HOST: str = resolve_app_host()
APP_PORT: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))
