# AION Production Hardening & Stabilization Plan

**Document Date:** August 31, 2026  
**Status:** AION deployed to Vercel production, ready for hardening  
**Mode:** Phases A-G (evidence-driven, not timeline-based)  
**Goal:** Production stabilization, reliability closure, observability, and continuous operations

---

## Overview

AION is operationally deployed and ready for systematic hardening. This plan sequences evidence-driven phases to identify and resolve production risks, restore type safety, stabilize durable storage, implement distributed reliability patterns, and establish observability.

**Product Identity Preserved:**
- AION remains a **conversation-first personal AI agent**
- Default interface stays simple (AionShell)
- Boardroom remains a hidden operational command environment
- No disruption to working functionality

**Key Principles:**
- All changes must be grounded in evidence (exact file paths, commands, results)
- Every finding must be classified (VERIFIED, REPORTED, REPO-LOCAL GAP, LIVE-ENVIRONMENT GAP, etc.)
- Production behavior takes precedence over repository assumptions
- Safety gates remain in place throughout all changes
- No production code changes without prior evidence phase

---

## Phase A: Evidence Correction

**Goal:** Reconcile repository assumptions with live production reality  
**Duration:** 1-2 days (read-only discovery)  
**Success Criteria:** Drift report, production verification checklist

### A1: Supabase Schema Parity Audit

**Current State:** Live Supabase has 27 tables in `aion` schema; repository definitions status unknown

**Actions:**

1. **Export Live Schema**
   ```bash
   # Via Supabase CLI (requires auth)
   supabase db pull --linked
   
   # Via psql connection
   pg_dump -h gtviwpevltuqhygsbsou.supabase.co -U postgres -d postgres \
     --schema=aion --schema-only > /tmp/live_schema.sql
   ```

2. **List Live Objects**
   ```sql
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'aion';
   SELECT view_name FROM information_schema.views WHERE table_schema = 'aion';
   SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'aion';
   SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema = 'aion';
   ```

3. **Compare Against Repository**
   - File: [aion/durable/postgres_schema.sql](aion/durable/postgres_schema.sql)
   - File: [aion/durable/migrate.py](aion/durable/migrate.py)
   - Identify: live-only tables, repo-only definitions, discrepancies

4. **Produce Drift Report**
   - Document: all 27 tables and their status (matches repo, live-only, repo-only)
   - Document: all views, functions, triggers, indexes
   - Document: RLS policies and grants
   - Classify: what must be fixed before next deployment

**Blockers:** Requires Supabase CLI access and production DB credentials  
**Deliverable:** `docs/SUPABASE_SCHEMA_AUDIT.md` (tables, views, functions, RLS, gaps)

---

### A2: Live Moltbook Mode Verification

**Current State:** Repository defaults to MOLTBOOK_MODE=mock; production mode unknown

**Action:**
```bash
# Check Vercel environment
vercel env pull
grep MOLTBOOK_MODE .env.local
```

**Deliverable:** Confirm production uses mock or live mode; document decision

---

### A3: PostHog Telemetry Baseline

**Current State:** PostHog connected but appears to use starter dashboard (no AION-specific events)

**Actions:**

1. Access PostHog dashboard
2. List all custom events currently being tracked
3. Verify no secrets/tokens/sensitive data in events
4. Document baseline: what events exist, what's missing, what's private

**Deliverable:** `docs/POSTHOG_AUDIT.md` (current events, gaps, privacy concerns)

---

### A4: Production Environment Checklist

**Verify all required env vars configured in Vercel:**

- ✅ OPENAI_API_KEY (required for chat)
- ✅ AION_OWNER_TOKEN (required for Boardroom)
- ✅ AION_DATABASE_URL (required for durability)
- ✅ AION_APPROVAL_TOKEN_PEPPER (required for approval signatures)
- ✅ CRON_SECRET (if using Vercel Cron)
- ✅ NEXT_PUBLIC_SUPABASE_URL (required for client)
- ✅ NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (required for client)
- ✅ GEMINI_API_KEY (optional, fallback)
- ✅ MOLTBOOK_API_KEY (optional, live mode)

**Deliverable:** Environment configuration verification report

**Blockers Complete:** All live environment gaps identified

---

## Phase B: Type & Contract Closure

**Goal:** Restore TypeScript type safety; clarify product contracts  
**Duration:** 2-3 days  
**Success Criteria:** 0 build-time TypeScript errors; all test contracts documented

### B1: TypeScript Error Inventory

**Current Issue:** `next.config.mjs` has `ignoreBuildErrors: true`

**Action:**

1. **Temporarily enable strict checking:**
   ```bash
   # Backup current config
   cp next.config.mjs next.config.mjs.backup
   
   # Remove ignoreBuildErrors flag
   # Edit next.config.mjs and remove: typescript: { ignoreBuildErrors: true }
   
   # Run strict check
   npm run build 2>&1 | tee /tmp/ts_errors.log
   npx tsc --noEmit --strict 2>&1 | tee /tmp/ts_errors_strict.log
   ```

2. **Inventory All Errors**
   - Parse output; group by file
   - Classify: defect, stale type definition, missing external type, acceptable difference
   - Example categories:
     - Missing `@types/package` package (fixable with npm install)
     - Incorrect type annotation (fix source code)
     - Type definition out of sync (update .d.ts)
     - Acceptable type difference (document with // @ts-expect-error + justification)

3. **Resolve or Document Each Error**
   - Fix actual defects in source code
   - Install missing @types packages
   - Add // @ts-expect-error comments with justification for unavoidable issues
   - Re-run `npm run build`

4. **Verify Build Success**
   ```bash
   npm run build
   # Expected: "Compiled successfully" with no skipped validation
   ```

**Deliverable:** 
- `docs/TYPESCRIPT_ERRORS.md` (all errors, classification, resolution)
- Clean build output (no "Skipping validation")

**File to Fix:** [next.config.mjs](next.config.mjs) (remove ignoreBuildErrors flag)

---

### B2: Capability Taxonomy Definition

**Current Issue:** Test expects 'ai' in capabilities; system returns ['automation', 'hosting', 'website']

**Action:**

1. **Understand Test Intent**
   ```bash
   grep -A 20 "test_capability_fit_supports_existing_yalitek_services" \
     tests/test_opportunity_qualification.py
   ```
   
2. **Review Capability Terms**
   ```python
   # aion/opportunity_qualification.py
   CAPABILITY_TERMS = {
     "website": ("website", "wordpress", ...),
     "hosting": ("hosting", "deployment", ...),
     "automation": ("automation", "workflow", ...),
     "ai": ("artificial intelligence", "ai agent", ...),
     # ...
   }
   ```

3. **Determine Product Contract:**
   - Is 'ai' a first-class capability or should it be decomposed?
   - If decomposed, what are the target capabilities? (research, automation, integration, modeling, etc.)
   - Should test opportunity include "AI agent" or "artificial intelligence" keywords?

4. **Resolve One Of:**
   - **Option A:** Update test to match actual behavior (if correct)
   - **Option B:** Add missing AI term synonyms to CAPABILITY_TERMS
   - **Option C:** Update test data if opportunity should trigger 'ai' match

5. **Verify Fix**
   ```bash
   python -m pytest tests/test_opportunity_qualification.py::test_capability_fit_supports_existing_yalitek_services -v
   ```

**Deliverable:**
- `docs/CAPABILITY_TAXONOMY.md` (canonical capabilities, synonyms, intended decomposition)
- All 134 tests passing

**Files to Update:** [aion/opportunity_qualification.py](aion/opportunity_qualification.py), [tests/test_opportunity_qualification.py](tests/test_opportunity_qualification.py)

---

### B3: Prompt Injection Attack Surface Audit

**Current State:** Partially protected; gaps identified in web research, Moltbook results, memory retrieval

**Actions:**

1. **Identify All Input Paths**
   - User conversation prompt → agent
   - Web research results → agent
   - Moltbook API responses → agent
   - Memory retrieval results → agent
   - External data (SAM.gov, federal contracts) → agent

2. **Audit Each Path for Prompt Injection**
   - File: [aion/moltbook/controlled_autonomy.py#L142-L165](aion/moltbook/controlled_autonomy.py#L142-L165) (has detection)
   - Files: Web research, memory retrieval, Moltbook integration (status unclear)
   - Identify: which paths sanitize, which don't, which need tests

3. **Add Test Cases**
   - Create test opportunities/prompts with injection payloads
   - Verify they don't leak into system instructions
   - Verify agent doesn't execute injected instructions

**Deliverable:**
- `docs/PROMPT_INJECTION_AUDIT.md` (attack vectors, mitigations, test status)
- New test cases: `tests/test_prompt_injection.py`

---

**Phase B Complete Criteria:**
- TypeScript builds without errors
- Capability taxonomy documented
- All 134 tests passing
- Prompt injection audit complete

---

## Phase C: Data Source-of-Truth

**Goal:** Establish durable storage reliability and reproducibility  
**Duration:** 3-4 days  
**Success Criteria:** Schema drift resolved, migration procedure validated, disaster recovery tested

### C1: Schema Parity Resolution

**Action (after Phase A drift report):**

1. **If Repository ≠ Live:**
   - Identify missing tables/views in repo
   - Document: why they exist in live (manual creation, abandoned feature, etc.)
   - Decide: should repo be updated to match live, or live cleaned up?
   - Update repo definitions to match live as source-of-truth

2. **If Live ≠ Repository:**
   - Identify missing tables/views in live
   - Determine: are they needed for current functionality?
   - If needed: add to live; update migration scripts
   - If obsolete: remove from repo

3. **Establish Version Control**
   - Tool: Liquibase, Alembic, or Supabase migrations
   - All schema changes tracked in git
   - Migration order documented and tested

**Deliverable:** Supabase schema matches repository definitions exactly

---

### C2: RLS Policy Audit

**Current State:** RLS policies exist but boundaries not verified

**Action:**

1. **Export All RLS Policies**
   ```sql
   SELECT * FROM pg_policies WHERE schemaname = 'aion';
   ```

2. **Verify Least-Privilege**
   - `aion_app` role has only necessary table/schema access
   - No public schema access from application
   - Service role clearly separated for admin operations

3. **Test Multi-Tenant Isolation (if applicable)**
   - If future multi-tenancy planned: verify RLS prevents cross-tenant leakage
   - Create test data with different tenant IDs; verify isolation

**Deliverable:** `docs/SUPABASE_RLS_AUDIT.md` (policies, roles, isolation verification)

---

### C3: Backup & Restore Validation

**Action:**

1. **Verify Supabase Backups Configured**
   - Check backup frequency (should be daily)
   - Check retention period (should be ≥ 30 days)

2. **Test Restore Procedure**
   - Initiate test restore from backup
   - Verify data integrity
   - Document restore procedure

3. **Disaster Recovery Runbook**
   - Document: how to restore from backup
   - Document: how to verify restored data
   - Document: communication during outage

**Deliverable:** `docs/DISASTER_RECOVERY.md` (backup strategy, restore procedure, runbook)

---

**Phase C Complete Criteria:**
- Live schema matches repository
- RLS policies verified
- Backup/restore tested
- Disaster recovery documented

---

## Phase D: Abuse & Reliability Hardening

**Goal:** Implement distributed rate limiting, provider failure handling, idempotency, and concurrency safety  
**Duration:** 4-5 days  
**Success Criteria:** Distributed rate limiter deployed; provider fallback working; all Phase 2 ops idempotent

### D1: Distributed Rate Limiter Implementation

**Current Issue:** Public `/agent` endpoint has no local rate limiting; relies on OpenAI limits

**Design:**

```
Identity: session_id + IP address
Window: sliding 1-minute window
Limits:
  - Per session: 10 requests/minute (burst)
  - Per IP: 100 requests/minute (sustained)
  - Per IP per hour: 5000 requests (abuse threshold)
Response: 429 Too Many Requests with Retry-After header
Storage: Vercel KV or Redis
```

**Implementation:**

1. **Install Vercel KV** (if using)
   ```bash
   npm install @vercel/kv
   ```

2. **Implement Rate Limiter Middleware**
   - File: [lib/rate-limiter.ts](lib/rate-limiter.ts) (new)
   - Track: session_id, IP, request count, window expiry
   - Return: { allowed: boolean, remaining: number, resetAt: Date }

3. **Add to `/api/aion/chat` Route**
   - File: [app/api/aion/chat/route.ts](app/api/aion/chat/route.ts)
   - Before OpenAI call: check rate limit
   - If exceeded: return 429

4. **Monitor & Log**
   - Log all rate limit violations
   - Alert on spike (e.g., > 100 violations/hour)

**Deliverable:** Rate limiter implemented and tested under load

---

### D2: Provider Failure Handling

**Current Behavior:** OpenAI unavailable → 502; no fallback or retry

**Design:**

```
Circuit Breaker: 
  - State: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
  - Transition: after 5 consecutive errors, enter OPEN for 60 seconds
  - Fallback: OpenAI (primary) → Gemini (secondary) → Vercel AI Gateway (tertiary)
Retry:
  - Exponential backoff: 1s, 2s, 4s
  - Max 3 retries
Timeout:
  - Hard 30-second per provider call
```

**Implementation:**

1. **Create Circuit Breaker Module**
   - File: [aion/circuit_breaker.py](aion/circuit_breaker.py) (new)
   - Track: failure count, last failure time, state
   - Provide: is_available(), record_success(), record_failure()

2. **Add Fallback Logic to `/agent` Endpoint**
   - File: [aion/agent_runtime.py](aion/agent_runtime.py)
   - Try: OpenAI
   - On failure: check circuit breaker; try fallback if available
   - Log: which provider used, why fallback triggered

3. **Test Failure Scenarios**
   - Mock OpenAI timeout → Gemini succeeds
   - Mock both fail → graceful error response
   - Circuit breaker recovery

**Deliverable:** Provider fallback tested and working

---

### D3: Idempotency for Phase 2 Operations

**Current State:** Approval ops use content-hash ✓; others unclear

**Action:**

1. **Audit All Writes**
   - File: [aion/main.py](aion/main.py) (owner endpoints)
   - File: [aion/commercial_execution.py](aion/commercial_execution.py)
   - Identify: which operations are idempotent, which aren't

2. **Implement Idempotency Keys**
   - Pattern: `operation_type:content_hash:owner_id`
   - Store in `aion.idempotency_keys` table: (key, operation_id, created_at)
   - Before write: check if key exists
   - If exists: return previous result
   - If new: execute and store key

3. **Test Double Delivery**
   - Simulate: approval approved, network fails, retry
   - Verify: operation succeeds once, retry returns same result
   - Verify: audit log shows single execution, re-delivered attempt

**Deliverable:** All Phase 2 writes are idempotent; test double-delivery scenario

---

### D4: Concurrency Safety (Distributed Lock)

**Current Issue:** Approval approved while execution in flight; race conditions possible

**Design:**

```
Lock Mechanism: Supabase advisory lock or Vercel KV
Lock Scope: per approval_id, per operation
Timeout: 30 seconds (if holder crashes, lock expires)
Atomicity: Check approval + kill switch + quota + acquire lock in single transaction
```

**Implementation:**

1. **Create Lock Manager**
   - File: [lib/distributed-lock.ts](lib/distributed-lock.ts) (new for Node.js side)
   - File: [aion/distributed_lock.py](aion/distributed_lock.py) (new for Python side)
   - Acquire: name, timeout
   - Release: name
   - Auto-release on context exit

2. **Wrap Approval Execution**
   - File: [aion/moltbook/approval.py](aion/moltbook/approval.py)
   - Before execution: acquire lock(approval_id)
   - Atomically: check approval valid + kill switch off + quota available
   - Execute: if all checks pass
   - Release lock

3. **Test Concurrency**
   - Start 2 concurrent requests for same approval
   - Verify: first succeeds, second gets 409 Conflict
   - Verify: execution happens only once

**Deliverable:** Distributed lock implemented; concurrency tests passing

---

### D5: Cold Start Session Recovery

**Current Issue:** SQLite sessions lost on Vercel redeploy; Postgres sessions should persist

**Action:**

1. **Add Session Schema Version**
   - Table: `aion.sessions` add column `schema_version INT`
   - Current: schema_version = 1

2. **Implement Migration Logic**
   - File: [aion/agent_runtime.py](aion/agent_runtime.py)
   - On load: check session.schema_version
   - If < current: apply migrations before resuming
   - If > current: reject (too new; might be data corruption)

3. **Test Cold Start**
   - Start session with user message
   - Trigger Vercel redeploy
   - Resume conversation
   - Verify: session restored, messages persist, conversation continues normally

**Deliverable:** Cold start session recovery tested and working

---

**Phase D Complete Criteria:**
- Rate limiter deployed and monitored
- Provider fallback tested
- All Phase 2 operations idempotent
- Distributed lock implemented
- Cold start recovery working

---

## Phase E: Observability

**Goal:** Establish comprehensive telemetry, alerts, and operational visibility  
**Duration:** 3-4 days  
**Success Criteria:** AION event taxonomy live; dashboard created; alerts configured

### E1: Event Taxonomy & Instrumentation

**Design AION-Specific Events:**

```
conversation_* (user interaction)
  conversation_started(session_id, client_type)
  conversation_completed(session_id, message_count, duration_s)
  
agent_response_* (LLM behavior)
  agent_response_succeeded(session_id, model, latency_ms)
  agent_response_failed(error_type, provider, latency_ms)
  
provider_* (model provider behavior)
  provider_selected(model, fallback_reason, timestamp)
  provider_fallback(from_model, to_model, reason)
  provider_timeout(provider, timeout_ms)
  provider_error(provider, error_code, message)
  
boardroom_* (owner operations)
  boardroom_opened(owner_id)
  boardroom_operation(operation_type, action)
  
capability_* (opportunity matching)
  capability_invoked(capability, result)
  capability_blocked(capability, reason)
  
approval_* (workflow)
  approval_requested(operation_type, approver)
  approval_approved(owner, operation_type)
  approval_denied(owner, reason)
  approval_failed(error)
  
memory_* (durable memory)
  memory_retrieved(query, results_count, relevance_score)
  memory_written(category, retention_days)
  memory_corrected(reason)
  
operation_* (phase 2 execution)
  operation_started(type, initiator)
  operation_completed(type, duration_s)
  operation_failed(type, error)
  operation_idempotent_retry(operation_id)
  
control_* (safety gates)
  kill_switch_toggled(state, reason, by)
  rate_limit_hit(identity_type, requests_in_window)
  quota_exceeded(owner_id, limit, current)
  
error (general)
  error(severity, component, message, context)
```

**Action:**

1. **Create Event Schema Document**
   - File: [docs/POSTHOG_EVENTS.md](docs/POSTHOG_EVENTS.md) (new)
   - Define each event, properties, privacy classification

2. **Add Instrumentation to Code**
   - Frontend: [components/aion-shell.tsx](components/aion-shell.tsx) (conversation events)
   - Frontend: [components/boardroom.tsx](components/boardroom.tsx) (boardroom events)
   - Backend: [aion/agent_runtime.py](aion/agent_runtime.py) (agent events)
   - Backend: [aion/main.py](aion/main.py) (operation events)
   - Backend: [aion/moltbook/approval.py](aion/moltbook/approval.py) (approval events)

3. **Verify Privacy & Security**
   - No raw prompts sent to PostHog
   - No API keys, tokens, secrets
   - No email addresses or sensitive personal data
   - No memory content (aggregate: memory_retrieved count only)

**Deliverable:** AION event schema documented and instrumentation deployed

---

### E2: Monitoring Dashboard

**Action:**

1. **Create PostHog Dashboard: "AION Health"**
   - **Conversations:** Daily active sessions, avg messages/session, completion rate
   - **Provider Health:** % requests by provider, error rate by provider, fallback frequency
   - **Performance:** P50/P95/P99 latency, error rate, 5xx rate
   - **Owner Operations:** Approvals/day, operations/day, executions/day
   - **Safety:** Rate limit hits, kill switch activations, quota violations

2. **Create Alerts**
   - Error rate > 5% → Slack alert
   - Avg latency > 3 seconds → Dashboard warning
   - Cost spike (e.g., > 2x baseline hourly spend) → Alert
   - Fallback to Gemini → Info log
   - Kill switch activated → Alert + Slack

**Deliverable:** PostHog dashboard live; alerts configured

---

### E3: Session Re-Authentication for High-Risk Operations

**Current Issue:** Kill switch, approvals, execution don't require re-auth

**Action:**

1. **Add Re-Auth Flow**
   - File: [lib/aion/owner-session.ts](lib/aion/owner-session.ts)
   - For kill-switch and approval actions: require owner to submit token again
   - Verify: timingSafeEqual against stored token
   - Log: all high-risk operations with owner + action + timestamp

2. **Test Flow**
   - Owner enters Boardroom
   - Toggles kill switch
   - System prompts: "Enter owner token to confirm"
   - Owner submits token
   - System verifies and toggles; logs audit event

**Deliverable:** High-risk operations require re-authentication

---

### E4: Structured Logging & Secret Sanitization

**Action:**

1. **Audit Error Responses**
   - File: [aion/main.py](aion/main.py) (error handlers)
   - Verify: no secrets, API keys, tokens in error messages
   - Verify: error messages are safe for client (no internal state details)

2. **Implement Log Sanitizer**
   - File: [aion/logging_utils.py](aion/logging_utils.py) (new)
   - Redact: API keys, auth tokens, email addresses, personal data
   - Pattern: replace sensitive values with `***redacted***`

3. **Configure Structured Logging**
   - All logs include: timestamp, severity, component, message, context
   - Vercel logs captured automatically

**Deliverable:** No secrets in logs or error responses

---

**Phase E Complete Criteria:**
- AION event taxonomy live and instrumented
- Health dashboard created
- Alerts configured
- Re-authentication for high-risk ops working
- Secrets sanitized in logs

---

## Phase F: End-to-End Validation

**Goal:** Verify all components work together; add integration and E2E tests  
**Duration:** 4-5 days  
**Success Criteria:** Integration tests pass; E2E tests cover critical paths; README updated

### F1: Integration Tests (UI ↔ API ↔ Backend)

**Current Gap:** No tests connecting UI components to API routes to Python backend

**Action:**

1. **Create Integration Test Suite**
   - File: [tests/test_integration_e2e.py](tests/test_integration_e2e.py) (new)
   - Framework: pytest + httpx (test Python backend) + jsdom/Puppeteer (test UI)

2. **Test Critical Paths**
   - **Path 1:** Send chat message → API route → FastAPI /agent → OpenAI → response → client
   - **Path 2:** Owner login → POST session → GET status → Boardroom opens
   - **Path 3:** Request approval → Approvals list updates → Approve → Execution blocked
   - **Path 4:** Kill switch toggle → /runtime/status changes → Boardroom reflects state
   - **Path 5:** Provider failure (OpenAI timeout) → Fallback to Gemini → Response succeeds

3. **Test Failure Paths**
   - API timeout → client gets 504
   - Malformed request → client gets 400
   - Auth missing → client gets 401/403
   - Rate limit exceeded → client gets 429

**Deliverable:** Integration test suite with 60%+ coverage of critical paths

---

### F2: End-to-End Browser Tests

**Current Gap:** No browser-based tests of UI flows

**Action:**

1. **Create E2E Test Suite**
   - File: [e2e/aion-conversation.spec.ts](e2e/aion-conversation.spec.ts) (new)
   - Framework: Playwright or Cypress

2. **Test Scenarios**
   - **Scenario 1:** Load page → see AionShell → type message → receive response → message history persists
   - **Scenario 2:** Navigate to Boardroom → enter owner token → see runtime status → toggle kill switch
   - **Scenario 3:** Click capability chip → see matching opportunities → approve draft
   - **Scenario 4:** Refresh page → previous conversation loads from durable memory
   - **Scenario 5:** Network error → retry logic works → message eventually delivers

3. **Test on Multiple Browsers**
   - Chrome/Edge (Chromium)
   - Firefox
   - Safari (if practical)

4. **Test on Multiple Devices**
   - Desktop
   - Tablet
   - Mobile (responsive design)

**Deliverable:** E2E test suite covering critical user flows

---

### F3: Documentation Update

**Current Issue:** README describes simpler architecture than actual system

**Action:**

1. **Update [README.md](README.md)**
   - Add architecture diagram (UI → API → Runtime → Supabase)
   - Document component hierarchy
   - Document data flow
   - Document deployment architecture

2. **Create [ARCHITECTURE.md](ARCHITECTURE.md)**
   - System design
   - Component responsibilities
   - Data model
   - API contracts
   - Provider integration patterns

3. **Link Supporting Docs**
   - [constitution/AION_CONSTITUTION.md](constitution/AION_CONSTITUTION.md)
   - [identity/AION_IDENTITY.md](identity/AION_IDENTITY.md)
   - [docs/MOLTBOOK_PHASE2.md](docs/MOLTBOOK_PHASE2.md)
   - [docs/CAPABILITY_TAXONOMY.md](docs/CAPABILITY_TAXONOMY.md)
   - [docs/DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md)

**Deliverable:** README and architecture documentation current and complete

---

### F4: Smoke Test Suite

**Action:**

1. **Create Smoke Tests**
   - File: [tests/test_smoke.py](tests/test_smoke.py) (new)
   - Quick checks: all endpoints reachable, Supabase connected, providers available
   - Run after every deployment

2. **Automate via Vercel**
   - Post-deployment: run smoke tests
   - If any fail: alert and auto-rollback

**Deliverable:** Smoke tests configured and working

---

**Phase F Complete Criteria:**
- Integration tests pass (60%+ critical path coverage)
- E2E tests pass (main user flows)
- README and architecture docs updated
- Smoke tests deployed

---

## Phase G: Continuous Operations

**Goal:** Establish long-term operational practices, security reviews, and scaling strategy  
**Duration:** Ongoing  
**Success Criteria:** Runbook in place; security reviewed; incident response defined

### G1: Security Review & Hardening

**Action:**

1. **CSRF Protection**
   - Verify SameSite=Strict on all cookies
   - Add CSRF token to form submissions if needed
   - Add tests for CSRF across owner routes

2. **Content Security Policy (CSP)**
   - Define strict CSP header
   - Whitelist: PostHog, OpenAI, Supabase, Vercel, Gemini
   - Test: no inline scripts, no unsafe CSS

3. **Subresource Integrity (SRI)**
   - Add SRI hashes to external CSS/JS libraries
   - Verify package updates maintain integrity

4. **API Security**
   - Rate limiting deployed ✓
   - Input validation on all endpoints
   - Output encoding in responses
   - JWT/token rotation policy

5. **Secrets Rotation**
   - Owner token rotation schedule (quarterly)
   - Approval token pepper rotation (quarterly)
   - Database password rotation (annually)
   - Document rotation procedures

**Deliverable:** `docs/SECURITY_HARDENING.md` (completed actions, residual risks)

---

### G2: Incident Response & Runbook

**Action:**

1. **Create Runbook** [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md)
   - **Deployment:** How to deploy; how to rollback
   - **Database:** How to backup; how to restore
   - **Monitoring:** How to access dashboards; what alerts mean
   - **Incidents:** How to respond to common failures
   - **Contacts:** Who to page; escalation path

2. **Incident Response Procedures**
   - **High Error Rate:** Check logs, identify component, page on-call
   - **Provider Outage:** Verify fallback working; alert customers if applicable
   - **Kill Switch Activated:** Investigate reason; reset if safe
   - **Rate Limit Spike:** Check for abuse; adjust limits if legitimate
   - **Database Failure:** Initiate restore procedure; verify data integrity

3. **Post-Incident Review**
   - Document: what failed, why, when
   - Document: how it was fixed
   - Document: preventive measures for next time
   - Share: lessons learned with team

**Deliverable:** Runbook documented and tested

---

### G3: Dependency & Security Updates

**Action:**

1. **Establish Update Cadence**
   - Weekly: check security advisories (GitHub, npm, PyPI)
   - Monthly: review and test dependency updates
   - Quarterly: major version updates

2. **Automate Updates (where possible)**
   - Renovate or Dependabot for npm/PyPI
   - Auto-merge non-breaking changes
   - Manual testing for breaking changes

3. **Track Vulnerabilities**
   - Use GitHub Security tab to track vulnerabilities
   - Set policy: resolve critical in < 7 days, high in < 30 days

**Deliverable:** Update and vulnerability management procedures in place

---

### G4: Cost Management & Optimization

**Action:**

1. **Monitor LLM Costs**
   - Track: requests by provider, tokens per request, cost per request
   - Set budget alerts
   - Optimize: prompt engineering, token usage, caching

2. **Database Optimization**
   - Monitor: query performance, connection count, storage growth
   - Index important queries
   - Archive old data

3. **Infrastructure**
   - Monitor: Vercel compute time, KV/Redis usage
   - Optimize: caching, early returns, efficient algorithms

**Deliverable:** Cost dashboard; optimization recommendations

---

### G5: Memory Governance Design

**Action:**

1. **Define Memory System**
   - **Working Memory:** current session state (ephemeral)
   - **Durable Memory:** cross-session facts (persistent)
   - **Provenance:** user-stated, system-verified, inferred, external-research
   - **Confidence:** high (verified), medium (inferred), low (external)

2. **Retention Policies**
   - **Active:** 30 days (recent conversations)
   - **Archive:** 30-365 days (old conversations)
   - **Delete:** upon user request or privacy event

3. **Correction Mechanism**
   - User can mark memory as incorrect
   - System creates conflict record (original + correction + timestamp)
   - Future queries favor corrections

4. **Privacy & Portability**
   - GDPR: export all personal data
   - GDPR: delete all personal data
   - Privacy: separate public vs private memory
   - Audit trail: who accessed what memory

**Deliverable:** `docs/MEMORY_GOVERNANCE.md` (system design, policies, procedures)

---

### G6: Scaling Strategy

**Action:**

1. **Database Scaling**
   - Monitor: connections, query latency, storage
   - Plan: sharding strategy if needed
   - Plan: read replicas for reporting

2. **API Scaling**
   - Current: Vercel serverless (auto-scales)
   - Monitor: function duration, cold start time
   - Plan: caching layer if throughput increases

3. **Cost Scaling**
   - LLM costs will grow with usage
   - Monitor: cost per conversation
   - Optimize: caching, batching, efficient prompts

**Deliverable:** Scaling plan and cost projections

---

**Phase G Complete Criteria:**
- Security review completed; hardening in place
- Runbook documented and validated
- Update/vulnerability procedures established
- Cost management and scaling strategy defined
- Memory governance documented

---

## Summary

This plan sequences AION hardening across 7 phases:

| Phase | Goal | Duration | Success Criteria |
|-------|------|----------|------------------|
| A | Evidence Correction | 1-2 days | Drift report; production verified |
| B | Type & Contract Closure | 2-3 days | TS clean; capabilities documented |
| C | Data Source-of-Truth | 3-4 days | Schema drift resolved; DR tested |
| D | Reliability Hardening | 4-5 days | Rate limiter, fallback, idempotency, locks |
| E | Observability | 3-4 days | Telemetry, dashboard, alerts |
| F | End-to-End Validation | 4-5 days | Integration & E2E tests; docs updated |
| G | Continuous Operations | Ongoing | Runbook, security, updates, governance |

**Total Timeline:** ~2-3 weeks (intensive) to reach Phase F completion; Phase G ongoing.

**Entry Point:** Begin with Phase A (read-only discovery) immediately. Phase B and C can start in parallel once Phase A findings are known. Phases D-G follow sequentially.

**Preservation:** All changes maintain AION's product identity (conversation-first, Boardroom hidden, safety gates always active).


4. **Create Health Check View**
   ```sql
   CREATE OR REPLACE VIEW public.aion_storage_status AS
   SELECT 
     'postgres' as backend,
     true as configured,
     'aion' as schema,
     (SELECT count(*) FROM information_schema.tables 
      WHERE table_schema = 'aion') as table_count;
   ```

5. **Set Up Least-Privilege Role**
   - Create role `aion_app` with only necessary permissions
   - Grant connect to database
   - Grant usage on schema `aion`
   - Grant all on tables in schema `aion` to `aion_app`
   - Revoke delete/drop permissions if desired

6. **Test Connectivity**
   ```bash
   export AION_DATABASE_URL="postgresql://aion_app:${PASSWORD}@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"
   python -c "from aion.durable.db import storage_status; print(storage_status())"
   ```

**Verifiable:** 
- Supabase console shows `aion` schema with 14 tables
- Health check endpoint returns `{backend: 'postgres', configured: true, schema: 'aion'}`
- No connection errors in logs

**Estimated Effort:** 2-3 hours (including testing and troubleshooting)

**Files:** [aion/durable/postgres_schema.sql](aion/durable/postgres_schema.sql), [app/api/storage/status/route.ts](app/api/storage/status/route.ts)

---

## Phase 2: Environment Configuration (Week 1)

**Goal:** Configure production-ready environment variables and test baseline functionality.

### 2.1 Generate Secure Tokens

**Action:**
1. Generate cryptographically-random tokens:
   ```bash
   # Owner token (32+ bytes)
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   
   # Approval pepper
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   
   # Cron secret
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   ```

2. Store in secure location (e.g., 1Password, Vercel secrets manager)

3. Document rotation policy (e.g., quarterly rotation)

**Verifiable:** Three tokens generated, documented, and ready for deployment

**Estimated Effort:** 30 minutes

---

### 2.2 Configure OpenAI Integration

**Action:**
1. Verify OpenAI account and API access
2. Select production model:
   - Recommended: `gpt-4o-2024-08-06` (specify exact version)
   - Document fallback model for cost control
3. Set up usage monitoring and alerts
4. Configure retry policy in production
5. Update `.env.example` with real model name

**Verifiable:** `AION_MODEL=gpt-4o-2024-08-06` set; `/health` returns `openai_configured: true`

**Estimated Effort:** 1 hour

**Files:** [.env.example](.env.example), [aion/config.py](aion/config.py)

---

### 2.3 Configure Gemini Integration (Optional)

**Action:**
1. Decide: deploy Gemini support or fallback only?
2. If deploying:
   - Set up Gemini API key
   - Document model version (e.g., `gemini-1.5-pro-2024-07-18`)
   - Add to test suite
3. If fallback only:
   - Document in DEPLOYMENT.md that `/gemini` returns 503
   - No action needed

**Verifiable:** Either `/gemini` endpoint works with test or is documented as intentionally disabled

**Estimated Effort:** 30 minutes (skip if not deploying Gemini)

---

### 2.4 Create DEPLOYMENT.md Guide

**Action:** Create comprehensive deployment checklist:

```markdown
# AION Deployment Guide

## Pre-Deployment

1. [ ] All 134 tests passing locally
2. [ ] TypeScript build successful with no ignored errors
3. [ ] Supabase schema created and verified
4. [ ] Environment variables generated

## Environment Variables (Vercel Secrets)

- OPENAI_API_KEY
- AION_MODEL=gpt-4o-2024-08-06
- AION_OWNER_TOKEN
- AION_APPROVAL_TOKEN_PEPPER
- CRON_SECRET
- AION_DATABASE_URL
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

## Deployment Steps

1. Push code to main branch
2. Vercel auto-deploys
3. Run health check: GET /health
4. Verify owner auth: POST /api/aion/owner-session with token
5. Test conversation: POST /api/aion/chat

## Post-Deployment Validation

1. [ ] /health returns ok=true, openai_configured=true
2. [ ] /runtime/status shows durable storage configured
3. [ ] Owner login succeeds with AION_OWNER_TOKEN
4. [ ] /agent endpoint accepts messages and returns responses
5. [ ] Audit logs created for all operations
6. [ ] Kill switch functional
```

**Verifiable:** DEPLOYMENT.md exists and is referenced in README.md

**Estimated Effort:** 1 hour

---

## Phase 3: Local Testing & Validation (Week 2)

**Goal:** Verify all components work correctly with production configuration in a staging environment.

### 3.1 End-to-End Conversation Test

**Test:** Full conversation flow from landing page to response

```bash
# 1. Start dev server
npm run dev

# 2. Open http://localhost:3000
# 3. Type message: "What is AION?"
# 4. Verify response received
# 5. Check browser console for errors
# 6. Check terminal for backend logs
```

**Verifiable:** Conversation completes; response appears on UI; no errors in console or server logs

**Estimated Effort:** 1 hour

---

### 3.2 Owner Authentication Flow Test

**Test:** Owner login and Boardroom access

```bash
# 1. Open browser to http://localhost:3000
# 2. Click "Terminal" or owner auth button
# 3. Enter AION_OWNER_TOKEN value
# 4. Verify HttpOnly cookie set: 
#    - Dev tools → Application → Cookies → aion_owner_session
# 5. Open Boardroom
# 6. Verify runtime status displays
```

**Verifiable:** HttpOnly cookie present; Boardroom loads; runtime status shows real gates

**Estimated Effort:** 1 hour

---

### 3.3 Runtime Status Verification

**Test:** Check all operational gates

```bash
curl -s http://localhost:8000/runtime/status | jq
```

Expected output:
```json
{
  "ok": true,
  "storage": {"backend": "sqlite", "configured": true},
  "moltbook": {"configured": true, "mode": "mock", "outbound_enabled": false},
  "autonomy": {"mode": "inactive", "dry_run": true, "live_writes_enabled": false},
  "kill_switch": {"engaged": false}
}
```

**Verifiable:** All safety gates show correct default state; no unexpected true values for execution

**Estimated Effort:** 30 minutes

---

### 3.4 Test Suite Full Run

**Action:** Run all tests with environment configured

```bash
python -m pytest tests/ -v --tb=short
```

Expected output:
```
====== 134 passed in XX.XX s ======
```

**Verifiable:** All 134 tests pass; no skipped or failed

**Estimated Effort:** 30 minutes

---

### 3.5 Build Verification

**Action:** Verify production build succeeds

```bash
npm run build
```

Expected output:
```
✓ Compiled successfully in X.Xs
Γöî  /(Static)
Γö£ /api/* (Dynamic)
...no errors
```

**Verifiable:** Build completes; next.out directory created; no type errors

**Estimated Effort:** 30 minutes

---

## Phase 4: Production Hardening (Week 2)

**Goal:** Add production-ready features before deployment.

### 4.1 Add Rate Limiting to Public `/agent` Endpoint

**Issue:** No local rate limit on public endpoint; relies entirely on OpenAI limits

**Implementation:**
1. Create `lib/rate-limiter.ts` with sliding window implementation
2. Wrap `/api/aion/chat` with per-session rate limit (e.g., 10 requests/minute)
3. Add fallback to Vercel KV if available
4. Return 429 Too Many Requests if exceeded

**Code Sketch:**
```typescript
// app/api/aion/chat/route.ts
const rateLimiter = new RateLimiter({
  windowSeconds: 60,
  maxRequests: 10,
  keyFn: (req) => clientSessionId(req),
});

if (await rateLimiter.isLimited(key)) {
  return Response.json({ error: "Rate limited" }, { status: 429 });
}
```

**Verifiable:** 
- Send 11 requests in 60 seconds; 11th returns 429
- Rate limit resets after 60 seconds

**Estimated Effort:** 2-3 hours

**Files:** lib/rate-limiter.ts, app/api/aion/chat/route.ts

---

### 4.2 Implement Observability

**Goal:** Add structured logging for production monitoring.

**Action:**
1. Install `winston` or `pino` for structured logging
2. Log to stdout (Vercel captures automatically)
3. Format as JSON for log aggregation
4. Add log levels: debug, info, warn, error

**Log Points:**
- Agent response latency
- API errors with status codes
- Owner operations (authenticated actions)
- Approval/kill switch changes
- Rate limit violations
- Moltbook integration status

**Verifiable:** `npm run dev` outputs structured JSON logs; log errors appear in Vercel dashboard

**Estimated Effort:** 3-4 hours

---

### 4.3 Add Monitoring Alerts

**Goal:** Notify on production incidents.

**Actions:**
1. Set up Vercel alerts:
   - Error rate threshold (e.g., > 5%)
   - Response time threshold (e.g., > 5s)
   - Cold start frequency
2. Set up custom alerts for:
   - Kill switch engaged
   - Approval token reuse attempt
   - Excessive rate limiting
3. Configure notification channel (email, Slack, etc.)

**Verifiable:** Alerts page in Vercel shows configured rules

**Estimated Effort:** 1-2 hours

---

## Phase 5: Deployment & Validation (Week 3)

**Goal:** Deploy to production and verify all systems operational.

### 5.1 Pre-Deployment Checklist

- [ ] All 134 tests passing
- [ ] TypeScript build error-free
- [ ] Supabase schema created and verified
- [ ] All environment variables ready
- [ ] DEPLOYMENT.md reviewed
- [ ] Owner token securely stored
- [ ] Monitoring configured
- [ ] Rate limiting implemented
- [ ] Observability in place
- [ ] Team sign-off on deployment

**Estimated Effort:** 1 hour (checklist review)

---

### 5.2 Deploy to Vercel

**Action:**
1. Merge all changes to main branch
2. Push to GitHub
3. Vercel auto-deploys (or manual trigger)
4. Monitor build logs for errors
5. Deployment completes in ~5-10 minutes

**Verifiable:** Vercel dashboard shows green checkmark; visit production URL

**Estimated Effort:** 15 minutes

---

### 5.3 Post-Deployment Validation

**Test 1: Health Check**
```bash
curl -s https://<PRODUCTION_URL>/health | jq
```
Verify: status=ok, openai_configured=true, moltbook configured

**Test 2: Conversation Flow**
- Visit https://<PRODUCTION_URL>
- Type message
- Receive response within 5 seconds
- Check browser console for errors

**Test 3: Owner Authentication**
- Click owner auth button
- Enter AION_OWNER_TOKEN
- Verify Boardroom loads
- Check runtime status

**Test 4: Monitor Logs**
- Open Vercel dashboard Logs
- Watch for errors over 30 minutes
- Verify no unexpected kill switch engagements

**Test 5: Verify Durable Storage**
```bash
curl -s https://<PRODUCTION_URL>/api/storage/status | jq
```
Verify: ok=true, backend=postgres, configured=true

**Verifiable:** All five tests pass; no errors in logs; deployment stable for 1 hour

**Estimated Effort:** 2 hours (including observation period)

---

## Phase 6: Post-Deployment Monitoring (Week 3-4)

**Goal:** Monitor production for issues and collect feedback.

### 6.1 Daily Operational Review

**Actions:**
- Check error rates (target: <1%)
- Check average response time (target: <2 seconds)
- Verify all endpoints responding
- Review audit logs for anomalies
- Monitor token usage and costs

**Frequency:** Daily for first week, then weekly

**Estimated Effort:** 15 minutes/day for 1 week, then 30 minutes/week

---

### 6.2 Collect Usage Metrics

**Actions:**
- Track conversation count
- Measure owner operations
- Monitor autonomy (should be inactive by default)
- Record kill switch activations

**Purpose:** Inform Phase 2 feature development

**Estimated Effort:** Automated; no manual effort

---

### 6.3 Owner Training

**Actions:**
- Document Boardroom functionality
- Walk owner through safety gates
- Explain kill switch procedure
- Review approval process
- Document escalation procedures

**Estimated Effort:** 2-3 hours (one-time)

---

## Phase 7: Post-Launch Enhancements (Weeks 4+)

**These are improvements that do NOT block deployment but improve user experience.**

### 7.1 Add Frontend Integration Tests

**Goal:** Prevent UI regressions

**Implementation:**
- Vitest + React Testing Library
- Test: conversation flow, auth dialog, boardroom interactions
- Target: 60%+ component coverage

**Estimated Effort:** 8-10 hours

**Priority:** Medium (next sprint)

---

### 7.2 Document Owner Charter Safely

**Goal:** Support private owner context without exposing it

**Implementation:**
- Verify `identity/OWNER_PRIVATE_CONTEXT.md` is never loaded into public instructions
- Test in isolation: Run agent with and without charter, verify no leakage
- Document in .gitignore and deployment notes

**Estimated Effort:** 2 hours

**Priority:** High (security)

---

### 7.3 Implement Approval Token Rotation

**Goal:** Add key rotation without invalidating pending approvals

**Implementation:**
- Add `POST /api/internal/approval-tokens/rotate` endpoint
- Generate new pepper; mark old tokens as deprecated
- Accept both old and new tokens for 30 days
- Audit trail for all rotations

**Estimated Effort:** 4-6 hours

**Priority:** Medium (operational hardening)

---

### 7.4 Expand Opportunity Sources

**Goal:** Add more lead discovery channels

**Candidates:**
- LinkedIn job postings (requires API)
- ProductHunt (public API available)
- Indie Hackers marketplace
- GitHub Sponsors
- Private grant databases

**Estimated Effort:** 4-6 hours per source

**Priority:** Low (nice-to-have; depends on business prioritization)

---

### 7.5 Add Gemini Integration Tests

**Goal:** Verify Gemini endpoint works in production

**Implementation:**
- Add integration test that calls Gemini API with test credentials
- Test error handling for rate limits, auth failures
- Document expected behavior vs OpenAI

**Estimated Effort:** 2-3 hours

**Priority:** Medium (completeness)

---

## Risk Mitigation

### Deployment Risks

| Risk | Probability | Severity | Mitigation |
|------|-------------|----------|------------|
| Supabase unavailable | Low | High | Verify connectivity before deploy; fallback to SQLite read-only |
| OpenAI quota exceeded | Very Low | High | Monitor usage; set up alerts; have cost control measures |
| Database migration fails | Low | High | Test migration locally first; have rollback plan |
| Auth token misconfigured | Medium | High | Validate token format before deploy; test login flow |
| TypeScript errors appear in prod | Low | High | Run full build locally before merge |

### Post-Deployment Risks

| Risk | Probability | Severity | Mitigation |
|------|-------------|----------|------------|
| Performance degrades | Low | Medium | Monitor p95 latency; scale as needed |
| Unexpected autonomy activation | Very Low | Critical | Kill switch always armed; audit every action |
| Approval token misused | Very Low | High | Implement token rotation; audit usage |
| Data corruption on migration | Very Low | Critical | Backup durable storage before migration |

---

## Success Criteria

### Phase 1 (Week 1)
✓ All 134 tests passing  
✓ TypeScript builds without errors  
✓ Supabase schema created and health check passing  

### Phase 2-3 (Week 2)
✓ Production configuration documented  
✓ All environment variables configured  
✓ End-to-end tests passing locally  
✓ Owner authentication working  
✓ Observability implemented  

### Phase 4-5 (Week 3)
✓ Deployed to production  
✓ Post-deployment validation passing  
✓ Zero critical errors in production logs  
✓ Response times < 2s p95  

### Phase 6+ (Weeks 4+)
✓ Error rate < 1%  
✓ Daily operational review shows stable behavior  
✓ Owner trained and using Boardroom  
✓ Usage metrics collected  

---

## Rollback Plan

If critical issues occur in production:

1. **Immediate Rollback (< 5 minutes)**
   - Revert Vercel deployment to previous commit
   - Engage kill switch if needed
   - Notify stakeholders

2. **Data Integrity Check**
   - Verify Supabase data consistency
   - Check audit logs for anomalies
   - Restore from backup if corrupted

3. **Post-Mortem**
   - Document root cause
   - Update test suite to catch issue
   - Plan fix for next deployment cycle


