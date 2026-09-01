---
applyTo: "**/*.py"
---

# Python / FastAPI development patterns for AION

Use these patterns when modifying runtime code in this repo.

## Core patterns

- Prefer `async def` for FastAPI handlers and I/O-bound logic.
- Keep request/response payloads in `aion/schemas.py` using Pydantic v2 models and `Field(...)` validation.
- Use `response_model=...` on route handlers when returning structured API data.
- Put endpoint logic in `aion/main.py` or `api/` and keep it consistent with the existing app structure.
- Validate required configuration before making provider calls; fail with `HTTPException` instead of allowing silent downstream errors.

## Error handling

- Reuse repo-specific error helpers from `aion/http_errors.py` for provider and owner-request failures.
- Wrap external provider calls with `try/except` and raise `upstream_provider_error(exc)` or `owner_request_error(exc)`.
- Return consistent status codes: 401/403 for auth issues, 429 for quota/rate limits, 503 for missing configuration.
- Treat Moltbook and owner-gated actions as safety-sensitive; do not bypass approval or token checks.

## Runtime and safety expectations

- Keep FastAPI app setup explicit: use a lightweight `lifespan` for startup validation and avoid crashing local development on optional settings.
- Preserve the default safety posture: controlled autonomy is inactive by default.
- For any branch that changes state, execution, or approvals, ensure the action is gated and documented in the Moltbook flow.
- Prefer factual provenance and evidence over speculative reasoning; keep runtime responses honest.

## Validation and contracts

- When changing schemas or endpoint contracts, regenerate the OpenAPI and inventory manifests:
  - `python scripts/generate_openapi.py`
  - `python scripts/generate_inventory.py`
- Add or update tests in `tests/` for new endpoints, validation rules, and safety behavior.
- Keep the project’s existing verification flow intact:
  - `python -m pytest tests/ -q`
  - `python scripts/check_openapi_contract.py`
  - `python scripts/check_inventory_contract.py`

## Repo references

- [AGENTS.md](../../AGENTS.md)
- [aion/main.py](../../aion/main.py)
- [aion/schemas.py](../../aion/schemas.py)
- [aion/http_errors.py](../../aion/http_errors.py)
- [docs/MOLTBOOK_CONTROLLED_AUTONOMY.md](../../docs/MOLTBOOK_CONTROLLED_AUTONOMY.md)
- [docs/MOLTBOOK_PHASE2.md](../../docs/MOLTBOOK_PHASE2.md)
