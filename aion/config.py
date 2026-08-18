"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MOLTBOOK_API_KEY: str = os.getenv("MOLTBOOK_API_KEY", "")
MOLTBOOK_BASE_URL: str = os.getenv(
    "MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1"
)
AION_MODEL: str = os.getenv("AION_MODEL", "gpt-5.6-terra")
AION_SESSION_DB: str = os.getenv("AION_SESSION_DB", "/tmp/aion_sessions.db")
AION_MAX_TURNS: int = int(os.getenv("AION_MAX_TURNS", "8"))
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))
