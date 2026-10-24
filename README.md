# AION

AION — The Alchemical Intelligence for Ontological Navigation.  
“The Guide who remembers who you are becoming.”

## Overview

AION is a personal AI operating system with:

- **Next.js UI** (`app/`, `components/`) — conversation surface, owner Boardroom, terminal diagnostics
- **FastAPI runtime** (`aion/`, `run.py`) — agent orchestration, Moltbook Phase 2 services, paper trading, controlled autonomy
- **Local intelligence** (Ollama) — secretless local reasoning in AION OS mode
- **Vercel Python functions** (`api/`) — production owner APIs, runtime status, scheduled ops

Demo fixtures in the conversation shell are explicitly labeled (`demo_fixture`). Live runtime evidence is available at `GET /api/runtime/status` and in the owner Boardroom.

## Project structure

```
AION/
├── aion/                 # FastAPI app, Moltbook, durable storage, autonomy
├── api/                  # Vercel Python serverless routes
├── app/                  # Next.js App Router (UI + /api/* BFF routes)
├── components/           # Boardroom, widgets, owner panels
├── lib/aion/             # Shared TS types, local reasoning, fact envelopes, mock router
├── openapi/              # Committed FastAPI OpenAPI contract
├── scripts/              # Inventory/OpenAPI generators and CI drift checks
├── tests/                # pytest suite
├── aion-inventory.yaml   # Generated capability + surface manifest
├── requirements.txt
└── run.py                # Local FastAPI entry point
```

## Setup

### Web UI

```bash
npm ci
cp .env.example .env.local   # fill optional cloud/owner keys only when needed
npm run dev
```

### Python runtime

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

FastAPI docs: `http://localhost:8000/docs`  
Next.js dev: `http://localhost:3000`

### AION OS local intelligence

Local mode does not require an OpenAI, Gemini, or Vercel key. With Ollama running on loopback and the local AION model installed:

```bash
export AION_RUNTIME_MODE=local
export AION_OLLAMA_URL=http://127.0.0.1:11434
export AION_LOCAL_MODEL=aion:latest
export AION_LOCAL_CONTEXT=4096
```

`POST /api/aion/chat` prefers Ollama in local mode. If Ollama is unavailable, AION only continues to a cloud path when a cloud provider/fallback is actually configured; otherwise it returns a truthful local-provider-unavailable response.

## Key surfaces

| Surface | Path | Notes |
|---------|------|-------|
| Conversation | `/` | Live chat via `/api/aion/chat`; local mode prefers Ollama |
| Owner Boardroom | `/owner` (auth required) | Live runtime gates, Moltbook research, opportunity review |
| Runtime status | `/api/runtime/status` | Truthful storage / local intelligence / Moltbook / autonomy snapshot |
| Owner APIs | `/api/owner/*` | Capability registry, commercial execution, acceptance evidence |

## Contracts & CI

```bash
npm run lint && npm run typecheck && npm run build
python -m pytest tests/ -q
python scripts/check_openapi_contract.py
python scripts/check_inventory_contract.py
```

Regenerate manifests after surface changes:

```bash
python scripts/generate_openapi.py
python scripts/generate_inventory.py
```

## Moltbook & autonomy docs

- Phase 1 read-only: `docs/MOLTBOOK_PHASE1.md`
- Phase 2 controlled growth: `docs/MOLTBOOK_PHASE2.md`
- Controlled autonomy (inactive by default): `docs/MOLTBOOK_CONTROLLED_AUTONOMY.md`
- Experiment ops cycle: `docs/MOLTBOOK_EXPERIMENT_OPS.md`

## Reasoning providers

In `AION_RUNTIME_MODE=local`, AION defaults to `aion:latest` through Ollama at `http://127.0.0.1:11434`, with a 4096-token local context. These defaults require no secret.

Outside local mode, or when a configured cloud fallback is needed, `AION_MODEL` defaults to `gpt-5.4` for the direct OpenAI path and the existing Vercel AI Gateway fallback chain remains available where configured.
