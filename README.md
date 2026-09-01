# AION

AION — The Alchemical Intelligence for Ontological Navigation.  
“The Guide who remembers who you are becoming.”

## Overview

AION is a personal AI operating system with:

- **Next.js UI** (`app/`, `components/`) — conversation surface, owner Boardroom, terminal diagnostics
- **FastAPI runtime** (`aion/`, `run.py`) — agent orchestration, Moltbook Phase 2 services, paper trading, controlled autonomy
- **Vercel Python functions** (`api/`) — production owner APIs, runtime status, scheduled ops

Demo fixtures in the conversation shell are explicitly labeled (`demo_fixture`). Live runtime evidence is available at `GET /api/runtime/status` and in the owner Boardroom.

## Project structure

```
AION/
├── aion/                 # FastAPI app, Moltbook, durable storage, autonomy
├── api/                  # Vercel Python serverless routes
├── app/                  # Next.js App Router (UI + /api/* BFF routes)
├── components/           # Boardroom, widgets, owner panels
├── lib/aion/             # Shared TS types, fact envelopes, mock router
├── openapi/              # Committed FastAPI OpenAPI contract
├── scripts/              # Inventory/OpenAPI generators and CI drift checks
├── tests/                # pytest suite (136+ tests)
├── aion-inventory.yaml   # Generated capability + surface manifest
├── requirements.txt
└── run.py                # Local FastAPI entry point
```

## Setup

### Web UI

```bash
npm ci
cp .env.example .env.local   # fill Supabase + owner/runtime keys as needed
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

## Key surfaces

| Surface | Path | Notes |
|---------|------|-------|
| Conversation | `/` | Live chat via `/api/aion/chat`; mock router for local UI demos |
| Owner Boardroom | `/owner` (auth required) | Live runtime gates, Moltbook research, opportunity review |
| Runtime status | `/api/runtime/status` | Truthful storage / Moltbook / autonomy snapshot |
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

## Default model

`AION_MODEL` defaults to `gpt-5.4` in both the Next.js chat route and FastAPI config. Override via environment variable.
