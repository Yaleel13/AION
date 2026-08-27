"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
# Legacy flat Moltbook vars kept for compatibility. Prefer
# ``aion.moltbook.load_moltbook_settings`` for validated Phase 1 config.
MOLTBOOK_API_KEY: str = os.getenv("MOLTBOOK_API_KEY", "")
MOLTBOOK_BASE_URL: str = os.getenv(
    "MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1"
)
MOLTBOOK_MODE: str = os.getenv("MOLTBOOK_MODE", "mock")
AION_MODEL: str = os.getenv("AION_MODEL", "gpt-4o-mini")
AION_SESSION_DB: str = os.getenv("AION_SESSION_DB", "")
if not AION_SESSION_DB:
    try:
        from aion.durable.paths import resolve_durable_paths

        AION_SESSION_DB = str(resolve_durable_paths().session_db)
    except Exception:
        AION_SESSION_DB = "/tmp/aion_sessions.db"
AION_MAX_TURNS: int = int(os.getenv("AION_MAX_TURNS", "8"))
AION_OPENAI_DAILY_COST_USD: float = float(os.getenv("AION_OPENAI_DAILY_COST_USD", "5.0"))
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))
