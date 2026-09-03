# AION go-live: start collecting real revenue

This is the owner runbook for turning on paid conversion. It does **not** set
Vercel secrets (this agent cannot write project env). It does **not** authorize
auto-comments on Reddit, GitHub, or Hacker News.

- Reddit public JSON is often 403 from datacenter IPs. HN and GitHub still
  feed the sales queue. If Reddit stays blocked in production, add an allowlisted
  HTTPS JSON source via `AION_COMMERCIAL_SCOUT_URLS` or reply to Reddit leads
  that arrive through Moltbook/HN instead.

## What the code now does

1. Discover buyer-intent posts on Moltbook, Hacker News, Reddit (r/forhire,
   r/freelance, r/webdev), and GitHub help-wanted issues.
2. Promote high-confidence public discoveries into the owner sales queue.
3. For **Moltbook** posts: optionally publish a policy-gated public reply with a
   checkout link when `MOLTBOOK_OUTBOUND_ENABLED` and `MOLTBOOK_EXECUTE_ENABLED`
   are true.
4. For **Reddit / GitHub / HN**: create an owner sales alert and attach a
   checkout link. **You** copy the draft and reply on that platform.
5. Stripe Checkout (when enabled) writes `payment_orders`. Fulfillment cron
   delivers paid work when `FULFILLMENT_CRON_ENABLED=true`.

## Required Vercel production env

Set these in the **AION** Vercel project (not Elaria). Never put secrets in
`NEXT_PUBLIC_*` variables.

### Rails (needed before a buyer can pay)

| Variable | Production value |
|---|---|
| `AION_DATABASE_URL` | Dedicated AION pooler URI, user `aion_app.gtviwpevltuqhygsbsou` |
| `AION_OWNER_TOKEN` | Long random token; used by Boardroom + owner APIs |
| `AION_APPROVAL_TOKEN_PEPPER` | Separate long random pepper |
| `CRON_SECRET` | Bearer token Vercel Cron sends to `/api/cron/revenue-ops` |
| `AION_KILL_SWITCH` | `false` (set `true` for emergency stop) |
| `STRIPE_SECRET_KEY` | Live (or test, then switch) Stripe secret |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret for the AION endpoint |
| `STRIPE_CHECKOUT_ENABLED` | `true` |

Webhook URL to configure in Stripe:

`https://<aion-production-host>/api/owner/checkout/webhook`

### Moltbook outbound (needed before AION comments in public)

| Variable | Production value | Notes |
|---|---|---|
| `MOLTBOOK_MODE` | `live` | Default in `.env.example` is `mock` |
| `MOLTBOOK_API_KEY` | Agent API key | |
| `MOLTBOOK_OUTBOUND_ENABLED` | `true` | Fail-closed until you set this |
| `MOLTBOOK_EXECUTE_ENABLED` | `true` | Requires outbound |
| `MOLTBOOK_CONTROLLED_AUTONOMY` | `true` only after quality review | Still inactive by default |
| `MOLTBOOK_AUTONOMY_DRY_RUN` | `false` only when live writes are intended | Default `true` |

### After the first successful paid test

| Variable | Production value |
|---|---|
| `FULFILLMENT_CRON_ENABLED` | `true` |

`.env.example` stays fail-closed on purpose. Copying it locally must not turn on
live outbound or live Stripe.

## Owner sequence (do this in order)

1. Confirm production deploy is READY on the commit that includes this runbook.
2. Set **rails** env vars. Redeploy or wait for env to bind.
3. Open `/owner` Boardroom → Outbound Gates. Kill switch, Postgres, owner token,
   cron secret, and Stripe should be green (`ready_for_revenue`).
4. Complete one **test-mode** Stripe checkout:
   - Prepare checkout from Sales Queue or Payment Rail.
   - Pay with a Stripe test card.
   - Confirm the webhook marks `payment_orders` paid (not duplicate on replay).
5. Switch Stripe keys to live only after the test path works.
6. Watch Sales Queue after the next `/api/cron/revenue-ops` run.
7. For Reddit/GitHub/HN rows: open the source, paste the draft, include the
   checkout URL. Do not share credentials. Do not spam.
8. Enable Moltbook outbound **after** you have reviewed drafted replies, then
   set `MOLTBOOK_OUTBOUND_ENABLED=true` and `MOLTBOOK_EXECUTE_ENABLED=true`.
9. Enable `FULFILLMENT_CRON_ENABLED=true` after a real paid order should be
   auto-fulfilled.

## Still owner-only (this agent cannot do them)

- Setting Vercel env vars (no env-write tool).
- Creating dedicated Stripe Payment Links per product. Emergency Diagnostic and
  AI Blueprint currently share the $49 Quick Tech Diagnostic link until you
  create distinct live links and update `aion/revenue/product_catalog.py`.
- Connecting an AION-specific PostHog project and event taxonomy.
- Granting this agent the AION Supabase project (`gtviwpevltuqhygsbsou`) in
  Supabase MCP (currently only YaliTek/Elaria are listed).
- Injecting private credentials tracked in GitHub issue #44.

## Safety that stays in force

- Kill switch remains authoritative.
- No auto-comment on Reddit, GitHub, or Hacker News.
- No unsolicited DMs, bids, grant applications, or live trading.
- Checkout creation does not charge the buyer; they must complete Stripe.
- Process-level Boardroom toggles do not persist on Vercel.
