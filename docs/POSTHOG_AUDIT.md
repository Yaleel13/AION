# PostHog Telemetry Audit

**Date:** 2026-09-03  
**Project:** `posthog-camel-ribbon` (id `507448`)  
**Organization:** yaleel30-gmailcom's projects  
**Base URL:** https://us.posthog.com/project/507448  
**Scope:** Phase A3 baseline — what events exist, whether they are AION-specific, and whether secrets appear in the taxonomy  
**Method:** Read-only PostHog MCP (`read-data-schema`). No dashboards, flags, or capture calls were created.

---

## Verified

- The MCP session is attached to project `507448` (`posthog-camel-ribbon`).
- Products **not** enabled on this project: session replay, exception autocapture, surveys, heatmaps.
- Integration connected: Vercel.
- Recent captured custom events are a **wellness / journal / meditation** product, not AION:

```text
subscription_status_refresh
journal_autosave_local
return_visitor_nudge_shown
login
practice_view
meditation_play
reminder_set
check_in_save
energy_reader_generate
journal_mood_select
learn_view
onboarding_complete
practice_complete
energy_reader_save
journal_create
sign_up
meditation_favorite
```

- `$pageview` is present. Sampled properties are standard posthog-js / GeoIP fields (`$current_url`, `$pathname`, `$host`, `$browser`, geo fields). No owner-token, API-key, or database-URL property names appear in the `$pageview` schema listing.
- PostHog catalog events such as `$ai_generation`, `$exception`, `$identify`, and `$mcp_tool_call` are defined but **not seen in the last 30 days**. They must not be reported as data this project is collecting.

## Repository comparison

AION application code (`aion/`, `app/`, `components/`, `lib/`) contains **no** PostHog SDK import or `capture(` call. The only in-repo mentions are documentation and a product-catalog resource row that labels PostHog as "connected".

That catalog row is **not** evidence that AION emits events. The connected project is collecting another product's events.

## Privacy

- No AION prompts, owner tokens, Stripe secrets, or Moltbook keys were observed in the `$pageview` property taxonomy.
- This is not a proof that no secret will ever be sent. It only shows the current event schema for `$pageview` does not include those fields.
- Because AION is not instrumented, AION conversations are not in this project's recent event list under an AION event name.

## Gaps

1. No AION event taxonomy (`aion_chat_turn`, `aion_owner_session`, `aion_kill_switch`, `aion_checkout_prepared`, cron cycle, …).
2. No AION health dashboard can be derived from current events.
3. Using this project for AION alerts would mix Elaria/wellness traffic with AION ops and produce false baselines.
4. MCP/Vercel access for this agent does not prove which browser origin is sending `$pageview`.

## Classification

| Item | Status | Severity | Phase |
|------|--------|----------|-------|
| PostHog "starter dashboard only" (Aug 31) | **Superseded** — events exist, but they are another product | Low | E |
| AION custom taxonomy | REPO-LOCAL GAP (not implemented) | Low | E |
| Secret leakage in PostHog | PARTIALLY VERIFIED for `$pageview` schema; AION not instrumented | Low | E |

## Follow-up

- If AION needs product analytics, create or switch to an AION-only PostHog project and instrument a small, non-secret event set at chat, owner auth, cron, and payment-ledger checkpoints.
- Until then, do not use PostHog charts as AION production health evidence.
