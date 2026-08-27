# AION
AION — The Alchemical Intelligence for Ontological Navigation  
“The Guide who remembers who you are becoming.”

## Overview

AION is a FastAPI service plus a Next.js boardroom UI. The API is a gateway to **OpenAI** and **Google Gemini**, hosts the primary `/agent` runtime, and includes a **Moltbook** integration:

- Phase 1: read-only research client (**mock by default**)
- Phase 2: owner-gated drafts, approvals, leads, and paper trading (**execute off by default**)
- Controlled autonomy: 14-day experiment engine (**inactive + dry-run by default**)

Committed defaults never enable live Moltbook writes. Activation is an explicit owner/environment step — see `docs/MOLTBOOK_CONTROLLED_AUTONOMY.md`.

## Project Structure

```
AION/
├── aion/                 # FastAPI package (agent, Moltbook, phase2, paper trading)
├── app/                  # Next.js App Router UI + API proxies
├── components/           # Boardroom / conversation UI
├── docs/                 # Phase, autonomy, and ops documentation
├── identity/             # Public identity + emissary docs (no secrets)
├── lib/aion/             # UI helpers (includes clearly labeled demo data)
├── scripts/              # Verification and ops scripts
├── tests/                # Pytest suite
├── .env.example          # Environment template (no real secrets)
├── requirements.txt
└── run.py                # API server entry point
```

## Setup

1. **Install API dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio   # for tests
   ```

2. **Configure environment** — copy `.env.example` to `.env` and set keys you need:
   ```
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=AIza...
   AION_OWNER_TOKEN=...          # required for /owner/* routes
   ```

3. **Run the API**
   ```bash
   python run.py
   ```
   API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

4. **Run the UI** (optional)
   ```bash
   npm install
   npm run dev
   ```
   UI: `http://localhost:3000` · Owner dashboard: `http://localhost:3000/owner`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (Moltbook phase2 status; autonomy default inactive) |
| POST | `/agent` | Primary AION agent runtime |
| POST | `/chatgpt` | ChatGPT (legacy) |
| POST | `/gemini` | Gemini (legacy) |
| GET | `/owner/dashboard` | Owner dashboard snapshot (bearer token) |
| POST | `/owner/*` | Campaign, approvals, leads, paper, kill-switch, execute, autonomy |

Moltbook docs: `docs/MOLTBOOK_PHASE1.md`, `docs/MOLTBOOK_PHASE2.md`, `docs/MOLTBOOK_CONTROLLED_AUTONOMY.md`, `identity/MOLTBOOK_EMISSARY.md`.

### Example – health

```bash
curl -s http://localhost:8000/health
```

### Example – ChatGPT (legacy)

```bash
curl -X POST http://localhost:8000/chatgpt \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the meaning of AION?"}'
```

## Defaults (accurate)

| Setting | Default in repo |
|---------|-----------------|
| `MOLTBOOK_MODE` | `mock` |
| `MOLTBOOK_OUTBOUND_ENABLED` | `false` (rejected if true in Phase 1 settings) |
| `MOLTBOOK_PHASE2_EXECUTE` | `false` |
| `MOLTBOOK_CONTROLLED_AUTONOMY` | `false` → mode `inactive` |
| `MOLTBOOK_AUTONOMY_DRY_RUN` | `true` |
| FastAPI package version | `0.2.0` |

## Running Tests

```bash
pytest tests/ -v
```
