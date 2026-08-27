# AION
AION  The Alchemical Intelligence for Ontological Navigation  “The Guide who remembers who you are becoming.”

## Overview

AION is a FastAPI-based service that acts as a unified gateway for receiving and forwarding data to AI providers — **ChatGPT (OpenAI)** and **Google Gemini** — plus a Phase 1 **read-only** Moltbook emissary client for research (mock by default).

The repository also contains a Next.js UI (`app/`, `components/`) for the AION boardroom interface.

## Project Structure

```
AION/
├── aion/
│   ├── __init__.py     # Package init
│   ├── config.py       # Environment-based configuration
│   ├── main.py         # FastAPI application & endpoints
│   ├── schemas.py      # Pydantic request/response models
│   └── services.py     # ChatGPT & Gemini service calls
├── tests/
│   └── test_endpoints.py
├── .env.example        # Template for environment variables
├── requirements.txt
└── run.py              # Server entry point
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys** – copy `.env.example` to `.env` and fill in your keys:
   ```
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=AIza...
   ```

3. **Run the server**
   ```bash
   python run.py
   ```
   The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (includes Moltbook Phase 1 status) |
| POST | `/agent` | Primary AION agent runtime |
| POST | `/chatgpt` | Send a message to ChatGPT (legacy) |
| POST | `/gemini` | Send a message to Gemini (legacy) |

Moltbook integration details: `docs/MOLTBOOK_PHASE1.md` and `identity/MOLTBOOK_EMISSARY.md`.

### Example – ChatGPT

```bash
curl -X POST http://localhost:8000/chatgpt \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the meaning of AION?"}'
```

### Example – Gemini

```bash
curl -X POST http://localhost:8000/gemini \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the meaning of AION?"}'
```

## Running Tests

```bash
pip install pytest httpx
pytest tests/ -v
```
