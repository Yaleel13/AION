# AION Audit Update — 2026-09-03

**Date:** 2026-09-03  
**Base audit:** [AION_REPO_AUDIT.md](AION_REPO_AUDIT.md) (2026-08-31)  
**Companion evidence:** [SUPABASE_SCHEMA_AUDIT.md](SUPABASE_SCHEMA_AUDIT.md) (2026-09-01), [POSTHOG_AUDIT.md](POSTHOG_AUDIT.md) (this update)  
**HEAD:** `4bbe68b` (`main`, merge of PR #127)  
**Scope:** Re-verify the August 31 findings against the current repository, classify remediations shipped through 2026-09-02, and record new production risks from the Stripe/revenue/cron work.

This document is evidence, not a change of safety policy. Controlled autonomy remains inactive by default. The time-bounded 6-hour revenue window expired at `2026-09-02T20:06:14Z`.

---

## Executive status

AION is still a conversation-first agent on Vercel with durable Postgres, owner gates, and a growing payment/fulfillment path. The August 31 primary blockers are **no longer current as written**. The live risk surface has moved to: serverless-local rate limiting, an unthrottled Next.js chat route, schema files that lag the live dump, a broken experiment-ops test module that fails collection, and observability that is not AION-specific.

| Original finding | 2026-08-31 | 2026-09-03 | Evidence |
|------------------|------------|------------|----------|
| TypeScript `ignoreBuildErrors` | VERIFIED CURRENT (true) | **RESOLVED** | `next.config.mjs` sets `ignoreBuildErrors: false`. `npx tsc --noEmit` exits 0. Security CI runs `npx tsc --noEmit` and `npm run build`. |
| Capability taxonomy (`ai` missing) | VERIFIED CURRENT (1 failing test) | **RESOLVED** | `CAPABILITY_TERMS["ai"]` includes `"ai"`. `test_capability_fit_supports_existing_yalitek_services` passes. |
| Supabase schema parity | REPORTED — NEEDS REPRODUCTION | **PARTIAL** | [SUPABASE_SCHEMA_AUDIT.md](SUPABASE_SCHEMA_AUDIT.md) exported 27 tables on 2026-09-01. Live dump now includes `payment_orders` (28 tables). `aion/durable/postgres_schema.sql` still has 19 tables; `payment_orders` is not in committed SQL. |
| Public `/agent` rate limit | VERIFIED CURRENT (none) | **PARTIAL** | FastAPI `/agent` uses `ClientSlidingWindowRateLimiter` (30/min default). Limiter is **in-process memory**, so it does not hold across Vercel isolates. Next.js `POST /api/aion/chat` has **no local throttle**. |

Python tests on this checkout: **160 passed** when `tests/test_experiment_ops.py` is excluded. That file **fails collection** (`ImportError: YALITEK_QUICK_DIAGNOSTIC_URL`). CI `python -m pytest tests/ -q` will fail until that module is aligned with `aion.revenue.product_catalog`.

---

## Phase A evidence (2026-09-03)

### A1. Supabase schema

**Verified from repository artifacts (no remote mutation):**

- Linked project in docs: `gtviwpevltuqhygsbsou`, schema `aion`.
- Committed dump: [supabase/aion_schema.sql](../supabase/aion_schema.sql) now has **28** `aion` tables. The table added since the 2026-09-01 inventory is `payment_orders`.
- Reference SQL: [aion/durable/postgres_schema.sql](../aion/durable/postgres_schema.sql) still defines the original 19 operational tables.
- Revenue SQL: [aion/durable/revenue_schema.sql](../aion/durable/revenue_schema.sql) defines `opportunities` only.
- Runtime SQLite fallback: [aion/opportunity_store.py](../aion/opportunity_store.py) creates `payment_orders` when `AION_DATABASE_URL` is unset. Postgres path assumes the table already exists.

**Still true from the 2026-09-01 audit:**

- Local `supabase/migrations/` is empty; remote history is 12 applied migrations, not reconstructed in-repo.
- RLS is enabled on `conversations`, `conversation_messages`, `memory_facts`, and (in the current dump) `payment_orders`, with **no policies** in the export.
- Grants are limited to `aion_app`.

**This agent's live MCP access does not include the AION project.** Supabase MCP listed only `YaliTekonline` (`ucejhhbxldmvbrltyazv`) and `supabase-elaria-yacht` (`lwmyyfrlqqyjbbjsunqn`). No schema changes were attempted against those projects.

### A2. Moltbook mode

| Surface | Observed |
|---------|----------|
| Repository default | `MOLTBOOK_MODE=mock` in `.env.example` and `aion/config.py` |
| Outbound / execute / autonomy | Fail-closed (`false` / dry-run `true`) unless explicitly enabled |
| Cron process override | `api/cron/ops.py` sets live outbound/execute/autonomy **only inside the expired 6-hour window** (`2026-09-02T14:06:14Z`–`2026-09-02T20:06:14Z`) and only for that process |
| Production env | **Unverified here.** Vercel MCP for this agent only lists the Elaria project `v0-elaria-ai-7c`, not AION |

Treat production Moltbook mode as still requiring an owner check in the Vercel project env. Do not infer live mode from the expired cron window.

### A3. PostHog

See [POSTHOG_AUDIT.md](POSTHOG_AUDIT.md). Summary: the connected PostHog project is ingesting a wellness/journal product taxonomy (`journal_create`, `meditation_play`, `energy_reader_generate`, …). AION source contains **no** `posthog.capture` / SDK instrumentation. No AION-specific event taxonomy exists.

### A4. Production environment

| Check | Result |
|-------|--------|
| Repo documents required secrets | `.env.example` lists owner, DB, cron, Stripe, Moltbook, and rate-limit vars |
| This agent can read AION Vercel env | **No.** Git deployment context only shows ElariaAI |
| This agent can read AION Supabase | **No.** MCP project list excludes `gtviwpevltuqhygsbsou` |
| Chat provider fallback | `app/api/aion/chat/route.ts` tries direct OpenAI, then Vercel AI Gateway models | 
| Cron auth | `CRON_SECRET` bearer required on revenue-ops and fulfillment |
| Stripe webhook | HMAC signature check in `StripeRuntime.verify_webhook_signature` |

Issue [#44](https://github.com/Yaleel13/aion/issues/44) (inject private runtime credentials) remains open and is the owner-side gate for live secrets.

---

## New and remaining findings

### FINDING U1: Experiment-ops tests fail collection

**Status:** VERIFIED CURRENT  
**Severity:** High (CI gate)  
**Classification:** REPO-LOCAL GAP  
**Files:** [tests/test_experiment_ops.py](../tests/test_experiment_ops.py), [aion/moltbook/experiment_ops.py](../aion/moltbook/experiment_ops.py)

`customize_lead_response` now matches products through `match_product_for_lead`. The test module still imports `YALITEK_QUICK_DIAGNOSTIC_URL`, which is no longer exported. `python -m pytest tests/ -q` is interrupted during collection. Security CI runs that exact command.

**Command:**

```bash
python -m pytest tests/test_experiment_ops.py --collect-only
```

**Result:** `ImportError: cannot import name 'YALITEK_QUICK_DIAGNOSTIC_URL'`

**Remediation:** Point the tests at `aion.revenue.product_catalog` (product name, checkout URL, price display) instead of the removed constant.

### FINDING U2: Next.js chat route is still unthrottled

**Status:** VERIFIED CURRENT  
**Severity:** Medium  
**Classification:** PRODUCTION RISK  
**File:** [app/api/aion/chat/route.ts](../app/api/aion/chat/route.ts)

This is the public conversation path. It has OpenAI → Gateway fallback but no per-IP or per-session limiter. The August 31 `/agent` finding was filed against this file and against FastAPI `/agent`. Only FastAPI was hardened.

### FINDING U3: Agent rate limiter is process-local

**Status:** VERIFIED CURRENT  
**Severity:** Medium  
**Classification:** PRODUCTION RISK  
**Files:** [aion/rate_limit.py](../aion/rate_limit.py), [aion/main.py](../aion/main.py)

`ClientSlidingWindowRateLimiter` stores timestamps in a process dict. On Vercel Python functions that budget is per isolate, not per client fleet. Burst traffic can fan out across cold starts. Phase D's distributed limiter (KV/Redis) is still the correct design.

### FINDING U4: `payment_orders` is live but not in reference SQL

**Status:** VERIFIED CURRENT  
**Severity:** High  
**Classification:** LIVE-ENVIRONMENT GAP  
**Files:** [supabase/aion_schema.sql](../supabase/aion_schema.sql), [aion/durable/postgres_schema.sql](../aion/durable/postgres_schema.sql), [aion/durable/revenue_schema.sql](../aion/durable/revenue_schema.sql), [aion/opportunity_store.py](../aion/opportunity_store.py)

The payment ledger is required for Stripe checkout, webhook replay protection, and fulfillment cron. Rebuilding Postgres from the committed `.sql` files would omit `payment_orders`, `conversations`, `conversation_messages`, `memory_facts`, `meta`, `positions`, `snapshots`, and `trades`.

**Remediation:** Fold the live dump's `payment_orders` (and the other live-only tables) into versioned SQL / migrations before the next schema change.

### FINDING U5: Expired 6-hour revenue window still mutates cron process env

**Status:** VERIFIED CURRENT  
**Severity:** Low (window closed) / Medium if dates are extended without review  
**Classification:** PRODUCTION RISK  
**File:** [api/cron/ops.py](../api/cron/ops.py)

Inside `[REVENUE_WINDOW_START, REVENUE_WINDOW_END)` the cron handler sets `MOLTBOOK_OUTBOUND_ENABLED`, `MOLTBOOK_EXECUTE_ENABLED`, and `MOLTBOOK_CONTROLLED_AUTONOMY` for **that process only**. The window is closed as of this audit. The hashed activation token and date bounds remain in source. Extending the dates would re-enable live outbound in cron without a separate policy review.

**Remediation:** Keep the window expired. Any future activation should be an explicit owner change with a new evidence record, not a silent date edit.

### FINDING U6: PostHog is not an AION production signal

**Status:** VERIFIED CURRENT  
**Severity:** Low  
**Classification:** POST-LAUNCH ENHANCEMENT  
**File:** [docs/POSTHOG_AUDIT.md](POSTHOG_AUDIT.md)

Do not treat the connected PostHog project as AION health telemetry. Active events belong to another product. AION has no custom capture calls.

### FINDING U7: Owner CSRF still unverified

**Status:** REPORTED — UNCHANGED  
**Severity:** Medium  
**Classification:** PRODUCTION RISK  

No CSRF token middleware was found in `app/` or `aion/`. Owner POSTs rely on the HttpOnly owner session / `AION_OWNER_TOKEN` bearer. SameSite=Strict cookies reduce browser CSRF risk; non-browser callers with a stolen token are unchanged.

---

## Remediations shipped since 2026-08-31 (do not re-open as original findings)

These are closed relative to the August 31 write-up. Residual gaps are listed above.

1. **Type safety gate restored** — `ignoreBuildErrors: false`; CI typecheck + build.
2. **Capability contract** — `ai` is a first-class capability; qualification tests pass (7/7 in that module).
3. **FastAPI `/agent` local limiter** — 429 + `Retry-After`; covered by `test_agent_endpoint_rate_limit`.
4. **Supabase export** — `docs/SUPABASE_SCHEMA_AUDIT.md` + `supabase/aion_schema.sql`.
5. **Chat provider fallback** — OpenAI Responses API failure falls through Vercel AI Gateway models in `app/api/aion/chat/route.ts`.
6. **Stripe rail** — signed webhooks, checkout prepare, payment ledger, fulfillment cron gated by `FULFILLMENT_CRON_ENABLED`.
7. **Sales-alert handoff** — owner-token gated `api/internal/sales-alerts.py`.
8. **Security headers** — `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy` on `/:path*` in `next.config.mjs`. CSP/SRI still absent.
9. **Cron rebind** — `vercel.json` hits `/api/cron/revenue-ops` and `/api/cron/fulfillment`.

---

## Test evidence (this update)

```text
npx tsc --noEmit
# exit 0

/workspace/.venv/bin/python -m pytest tests/ --ignore=tests/test_experiment_ops.py -q
# 160 passed

/workspace/.venv/bin/python -m pytest tests/test_experiment_ops.py --collect-only
# ERROR: cannot import name 'YALITEK_QUICK_DIAGNOSTIC_URL'
```

---

## Recommended next work (priority)

1. Repair `tests/test_experiment_ops.py` so Security CI pytest is green.
2. Add `payment_orders` (and other live-only tables) to committed schema/migrations.
3. Put a limiter on `POST /api/aion/chat` and replace the in-process agent limiter with a shared store.
4. Confirm production `MOLTBOOK_MODE`, Stripe, and `AION_DATABASE_URL` in the AION Vercel project (owner / issue #44).
5. Decide whether AION should have its own PostHog project and event taxonomy, or stop claiming PostHog as AION observability.

Do not treat the expired 6-hour window as current authority to run live outbound.
