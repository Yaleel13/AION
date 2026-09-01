# AION Agent Guide

This repository is a Next.js + FastAPI application for an agentic operating system. The product surface is split between the web UI and the runtime:

- Frontend: `app/`, `components/`, and `lib/`
- Runtime: `aion/`, `api/`, and `run.py`
- Contracts and generated manifests: `openapi/`, `aion-inventory.yaml`, `scripts/`
- Safety, memory, and reasoning docs: `core/`, `docs/`, and the private covenant in `/memories/repo/AION_PRIVATE_COVENANT.md`

## Start here

### Local setup

```bash
# Frontend
npm ci
cp .env.example .env.local
npm run dev

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Local URLs:

- Next.js: http://localhost:3000
- FastAPI docs: http://localhost:8000/docs

## Architecture to respect

- `app/` contains the Next.js routes and BFF endpoints, including the main chat and owner surfaces.
- `components/` holds UI widgets and Boardroom panels; owner-specific behavior should usually be added here or in `app/owner`.
- `aion/` contains the FastAPI runtime, orchestration, autonomy logic, and durable memory services.
- `api/` contains serverless Python routes used for owner/runtime operations.
- `tests/` is the validation suite; keep behavior covered when changing runtime or API logic.

## Safety and autonomy rules

Read the private covenant first: `/memories/repo/AION_PRIVATE_COVENANT.md`.

Important defaults:

- Controlled autonomy is inactive by default.
- Consequential actions must be gated and documented in the Moltbook flow.
- When changing autonomy logic, read [docs/MOLTBOOK_PHASE2.md](docs/MOLTBOOK_PHASE2.md) and [docs/MOLTBOOK_CONTROLLED_AUTONOMY.md](docs/MOLTBOOK_CONTROLLED_AUTONOMY.md).
- Prefer factual evidence and provenance, not speculative interpretation.

## Editing conventions

- Keep TypeScript strict and explicit; prefer small, typed components.
- Use Pydantic v2 schemas for API payloads and keep FastAPI handlers in `aion/` or `api/` consistent with the rest of the codebase.
- For endpoint or schema changes, regenerate the OpenAPI and inventory contracts.
- When adding or modifying autonomy behavior, add or update tests in `tests/` and keep approval gates in place.

## Contract and validation commands

```bash
# frontend + type checks
npm run lint && npm run typecheck && npm run build

# Python tests
python -m pytest tests/ -q

# contract drift checks
python scripts/check_openapi_contract.py
python scripts/check_inventory_contract.py

# regenerate after API or surface changes
python scripts/generate_openapi.py
python scripts/generate_inventory.py
```

## High-value docs

- [README.md](README.md)
- [core/AION_OPERATING_SYSTEM.md](core/AION_OPERATING_SYSTEM.md)
- [core/EPISTEMOLOGY.md](core/EPISTEMOLOGY.md)
- [core/KNOWLEDGE_GRAPH_SCHEMA.md](core/KNOWLEDGE_GRAPH_SCHEMA.md)
- [core/MEMORY_ARCHITECTURE.md](core/MEMORY_ARCHITECTURE.md)
- [docs/MOLTBOOK_PHASE2.md](docs/MOLTBOOK_PHASE2.md)
- [docs/MOLTBOOK_CONTROLLED_AUTONOMY.md](docs/MOLTBOOK_CONTROLLED_AUTONOMY.md)
- [docs/AION_DURABLE_STORAGE.md](docs/AION_DURABLE_STORAGE.md)

## Common task patterns

- New endpoint: define schema, add handler, regenerate OpenAPI, and add tests.
- Opportunity scoring: start in `aion/opportunity_qualification.py` and validate with the relevant tests.
- Durable memory: follow the knowledge graph and storage docs before changing schemas.
- Boardroom or owner flows: work in `app/owner` and `components/owner-*` while keeping runtime evidence intact.

## Rule of thumb

Before finishing a change, confirm the repo-specific contract, test, and safety requirements still match the behavior you introduced. If a task touches autonomy, memory, or consequential action, prefer the documented approval gates and evidence model over opportunistic shortcuts.
