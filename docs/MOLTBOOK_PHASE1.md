# Moltbook Integration — Phase 1 (Read-Only)

## Purpose

Give AION a **safe, read-only** foundation for learning from Moltbook without
posting, messaging, spending, contracting, or autonomous outreach.

Moltbook may later support research, networking, opportunity discovery, brand
awareness, and lead generation for YaliTek Online. Phase 1 does **not** enable
those outbound behaviors.

## Trust boundary

- All Moltbook content is **untrusted external data**.
- It must never override AION's constitution, identity, repository policies, or
  owner approval requirements.
- Prompt-injection style instructions found in posts/comments are content only.

## Setup

1. Copy `.env.example` to `.env` (if not already present).
2. Leave `MOLTBOOK_MODE=mock` for local development (no live network, no key).
3. For live read-only access (optional):
   - Register/claim the agent manually using the official Moltbook flow
     documented in `identity/MOLTBOOK_EMISSARY.md`.
   - Store the API key only in a secrets manager / local `.env` (never commit).
   - Set `MOLTBOOK_MODE=live` and `MOLTBOOK_API_KEY=...`.
4. Keep `MOLTBOOK_OUTBOUND_ENABLED=false` (Phase 1 rejects `true` at config load).

## Permissions (Phase 1)

Allowed:

- `GET /agents/me` — profile
- `GET /agents/status` — claim status
- `GET /posts` — feed
- `GET /posts/{id}` — single post
- `GET /posts/{id}/comments` — comments
- `GET /search` — semantic search
- `GET /submolts` / `GET /submolts/{name}` — communities

Denied (blocked in code + approval gate):

- create/delete posts, comments, votes
- follow / subscribe
- profile updates, registration from this runtime
- any spending, contracts, or account changes

## Limitations

- No scheduled heartbeat / autonomous polling loop is enabled.
- No agent tools expose Moltbook yet (agent runtime remains diagnostic-only).
- Live mode still requires a claimed agent API key owned by you.
- Mock mode returns synthetic payloads marked `untrusted: true`.

## Security controls

- Typed settings validated on load (`aion.moltbook.settings`).
- Live base URL restricted to `https://www.moltbook.com`.
- Timeouts, client-side rate limiting, retries with backoff on 429/5xx.
- Structured audit logs with credential/PII redaction.
- Outbound methods raise `MoltbookOutboundDisabledError` and record an
  approval proposal for future Phase 2 review.

## Rollback

1. Set `MOLTBOOK_MODE=mock` (or unset live key).
2. Or remove/rename `aion/moltbook/` and restore the previous single-file client
   from git history if needed.
3. No database migrations are involved in Phase 1.

## Proposed approval system (Phase 2 preview)

`aion.moltbook.approval.OutboundApprovalGate` records proposed outbound actions
(`create_post`, `comment`, `follow`, etc.). In Phase 1:

1. Code may **propose** an action for human review.
2. Even an "approved" decision **cannot execute**.
3. Execution remains disabled until you explicitly accept a Phase 2 design.

## Usage (Python)

```python
from aion.moltbook import create_client

client = create_client()  # mock by default
profile = await client.profile()
feed = await client.feed(sort="hot", limit=10)
# All payloads are untrusted data.
```

## Related docs

- `identity/MOLTBOOK_EMISSARY.md` — public identity and launch sequence
- `constitution/AION_CONSTITUTION.md` — non-negotiable priorities
- Official API skill: https://www.moltbook.com/skill.md
