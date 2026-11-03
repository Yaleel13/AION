# Local Boardroom owner panels

With `AION_RUNTIME_MODE=local`, the browser uses the existing same-origin
`/api/owner/*` session-authenticated bridges. Their server-side bearer requests
to explicit `/api/internal/<name>` routes are rewritten by Next.js to the
configured FastAPI runtime (default `http://127.0.0.1:8000`). There is no internal
wildcard.

The runtime reuses the existing serverless handlers for acceptance, capabilities,
operator briefing, outbound gates, sales alerts, Moltbook research, preparation,
reviews, approvals, and commercial execution. Registration adds local-mode and
loopback and bearer guards. Each handler retains its bearer policy and business approval
gates; the browser bridges retain session authentication and POST CSRF checks.
Other serverless internal handlers are not registered by this adapter.

The complete new surface is 18 method/path pairs on 11 exact paths:

- GET only: acceptance, capabilities, operator-briefing.
- GET and POST: outbound-gates, sales-alerts, moltbook-research,
  moltbook-preparation, moltbook-reviews, moltbook-approvals, commercial-execution.
- POST only: conversation, an authenticated alias for the local memory service.
  Its load/append/search/remember/forget/replace/facts actions all require the
  runtime bearer. Server-side chat, memory loading, and the owner inspector
  supply it. The pre-existing `/local-memory` loopback-only endpoint keeps its
  legacy behavior and is no longer exposed by the conversation rewrite.

The seven mutation routes retain checkout preparation, research scanning,
preparation/review updates, approval/execution, and process-level gate toggles.
Owner bridges require their existing session and POST CSRF marker before any
upstream request. The owner memory inspector's internal POST is a read-only
facts operation behind a session-protected GET bridge.

Unexpected runtime exceptions produce generic JSON 500 responses without private
diagnostics. A shared server-side upstream boundary disables redirects and
normalizes non-JSON responses to JSON 502, connection failures to JSON 503,
and server failures to redacted JSON errors. It preserves actionable 4xx policy
errors and the specific missing-Postgres 503 below. Raw upstream bodies are not
returned or logged by this boundary.

Before this routing connection, the bridges received Next's HTML 404 page.
Some preserved 404; others failed JSON parsing and returned 500. The handlers
were also absent from the local runtime.

Production Reliability Acceptance requires `AION_DATABASE_URL` for durable
Postgres evidence. Without it, the existing handler returns 503; the bridge now
surfaces `Durable Postgres is not configured` as the panel's error message.
SQLite-backed owner views can still load. Reading stored research and review
data does not establish live Moltbook availability or authorize external writes.
Live research and commercial execution continue to require their existing
provider configuration, owner approvals, independent gates, and kill-switch
checks. No configuration is changed by loading these panels.

Cloud mode keeps the existing Vercel serverless routing. The runtime adapter
fails closed outside local mode. It does not add any MCP tools.
