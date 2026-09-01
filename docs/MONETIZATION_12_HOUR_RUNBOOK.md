# AION 12-Hour Monetization Runbook

This runbook prepares AION to discover and qualify legitimate opportunities, draft public Moltbook replies, collect owner approval for exact content, create owner-approved Stripe Checkout sessions, and record payment outcomes. It does not authorize unsolicited messaging, automatic applications or bids, live trading, wallet transfers, or spending.

## Go/no-go gates

Do not begin the live window until every required gate is green:

1. Production deployment is `READY` on the intended commit.
2. `GET /api/storage/status` reports configured Postgres storage in schema `aion`.
3. `aion.payment_orders` exists and is writable by `aion_app`.
4. Owner authentication works in `/owner`.
5. Moltbook live read-only research succeeds.
6. Stripe webhook signing is configured and a test-mode checkout completes end to end.
7. `AION_KILL_SWITCH=false`; the owner knows how to set it to `true` immediately.
8. Outbound and execute gates remain false until the owner reviews the prepared content and explicitly activates them.

## Required production configuration

Server-only values:

- `AION_DATABASE_URL`: dedicated AION transaction-pooler URL using the least-privilege `aion_app.<project-ref>` user.
- `AION_OWNER_TOKEN`
- `AION_APPROVAL_TOKEN_PEPPER`
- `CRON_SECRET`
- `MOLTBOOK_MODE=live`
- `MOLTBOOK_API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_CHECKOUT_ENABLED=true`

Initial safety values:

- `AION_KILL_SWITCH=false`
- `MOLTBOOK_OUTBOUND_ENABLED=false`
- `MOLTBOOK_EXECUTE_ENABLED=false`
- `MOLTBOOK_CONTROLLED_AUTONOMY=false`
- `MOLTBOOK_AUTONOMY_DRY_RUN=true`
- `FULFILLMENT_CRON_ENABLED=false`

Never place database passwords, Stripe secrets, Moltbook keys, owner tokens, or approval peppers in source control or browser-visible variables.

For project `gtviwpevltuqhygsbsou`, the transaction-pooler username must be `aion_app.gtviwpevltuqhygsbsou`, not `postgres`. Copy the transaction-pooler URI from the Supabase Connect dialog and substitute the current `aion_app` password in the secret manager. The direct-host template shown by Supabase is not a usable production secret for this deployment.

## Hour 0-1: prove the rails

1. Verify storage and owner authentication.
2. Run Moltbook read-only research and inspect the returned provenance.
3. Create a Stripe test-mode checkout for a test opportunity.
4. Complete the test checkout, confirm one signed webhook is processed, replay the same event, and confirm it is reported as a duplicate.
5. Manually fulfill the paid test order and confirm the opportunity ledger records realized value.
6. Delete or clearly label the test opportunity; never count test revenue as real revenue.

If any step fails, stop the live window and keep outbound disabled.

## Hour 1-3: research and qualify

1. Run the scheduled-safe opportunity scan or trigger the owner research surface.
2. Review the top opportunities by evidence, fit, expected value, time, cost, and risk.
3. Reject unverifiable, speculative, prohibited, capital-requiring, or low-fit items.
4. Select at most three zero-upfront-cost opportunities that can plausibly be delivered with current YaliTek/AION capability.
5. Build pursuit packets with scope questions, delivery assumptions, and an owner-reviewed price strategy.

## Hour 3-6: prepare exact outreach

1. Prepare public Moltbook comments only for eligible public posts.
2. Inspect exact content, destination, content hash, and idempotency key.
3. Remove claims that are not backed by current capability or evidence.
4. The owner explicitly approves or rejects each exact message.
5. Enable `MOLTBOOK_OUTBOUND_ENABLED=true` only when approval operations are required.
6. Enable `MOLTBOOK_EXECUTE_ENABLED=true` only for the short execution window; execute single-use approvals individually.
7. Return both gates to false after the approved batch.

No DMs, email moves, bids, applications, contracts, price promises, customer-file requests, or account-access requests are authorized by this runbook.

## Hour 6-10: respond and close safely

1. Monitor public replies and qualify any response before continuing.
2. Ask only non-sensitive scope, timeline, budget, and decision-process questions.
3. Bring pricing, commitments, off-platform movement, file access, and contract acceptance to the owner.
4. For an owner-approved offer, create a Stripe Checkout session tied to its opportunity ID and commercial execution ID.
5. Treat payment as real only after the signed webhook records the event in durable storage.

## Hour 10-12: fulfill and reconcile

1. Review paid orders in the owner dashboard.
2. Fulfill only deliverables whose scope and authorization are complete.
3. Manually trigger fulfillment first. Enable `FULFILLMENT_CRON_ENABLED=true` only after one successful test and one successful real manual fulfillment.
4. Verify realized revenue attribution, delivery evidence, customer communication, and audit receipts.
5. Disable outbound and execute gates, build the daily report, and record lessons for the next cycle.

## Stop conditions

Immediately set `AION_KILL_SWITCH=true` and disable Moltbook outbound/execute if any of the following occurs:

- moderation or account warning;
- unexpected destination or changed exact content;
- duplicate or unexplained outbound activity;
- quota/rate-limit anomaly;
- invalid Stripe signature or unexplained payment state;
- database durability/authentication failure;
- request for secrets, credentials, unlawful work, deception, or funds;
- any action outside the owner-approved scope.

## Success criteria

The 12-hour window is successful if it produces verified qualified leads, owner-approved outreach, and a durable, attributable payment or strong next-step signal without policy violations, secret exposure, unauthorized commitments, or untracked execution. Revenue is not guaranteed and must never be fabricated.
