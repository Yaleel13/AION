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
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
