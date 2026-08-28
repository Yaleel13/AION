from pathlib import Path

from google.adk.cli.fast_api import get_fast_api_app

BASE_DIR = Path(__file__).resolve().parent

app = get_fast_api_app(
    agents_dir=str(BASE_DIR),
    allow_origins=["*"],
    web=False,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "opportunity-navigator",
        "framework": "google-adk",
        "model": "gemini-3.7-flash",
    }
