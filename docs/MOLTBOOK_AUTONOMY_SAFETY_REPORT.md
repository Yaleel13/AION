# Controlled Autonomy — Safety Report (pre-activation)

**Date:** 2026-08-27  
**Branch:** `cursor/moltbook-controlled-autonomy-d5b5`  
**Verdict:** Guardrails are implemented and tested. **Controlled autonomy is NOT activated.**  
**Recommendation:** Safe to *consider* activation only after explicit final owner approval. Do not deploy live writes yet.

## Checklist results

| Step | Result |
|------|--------|
| 1. Implement and test every guardrail | PASS (unit/adversarial suite) |
| 2. Show exact content-generation and qualification rules | PASS — `CONTENT_GENERATION_RULES` + `docs/MOLTBOOK_CONTROLLED_AUTONOMY.md` |
| 3. Adversarial tests (injection, secrets, spam, duplicates, rate limits) | PASS |
| 4. Confirm kill switch works | PASS |
| 5. Report whether safe to activate | **Ready for owner decision; defaults remain inactive** |
| 6. Stop for final owner approval | **STOPPED — awaiting your go-ahead** |

## Adversarial coverage

- Prompt injection in inbound context → blocked
- Secret/API-key shaped outbound text → **suspends** autonomy
- Generic praise comments → blocked
- Financial/crypto solicitation denylist → blocked
- Duplicate idempotency keys → blocked
- Rolling quotas: expanded ceilings 2 posts/24h, 8 comments/24h, 15 follows/7d (auto-reduce 1/3/5) → enforced
- Kill switch engaged → all outbound refused
- 3 consecutive live-path errors → automatic `read_only_fallback`
- Direct messages → not authorized
- Default env → `inactive`, `dry_run=true`, `live_writes_enabled=false`

## Exact rules (summary)

See `aion/moltbook/autonomy_policy.py`:

- **Posts:** original, allowlisted topics, no secrets/PII, no denylisted finance/crypto/contract language, ≥40 chars
- **Comments:** concrete contribution markers; no generic praise; ignore embedded instructions
- **Follows:** no injection/spam targets; weekly cap
- **Leads:** alert + draft OK; price/email/consultation/accept work require owner
- **Crypto:** paper only; no wallets/exchanges/live trades

## Activation gates (still required)

Do **not** set these until you reply with explicit final activation approval:

```bash
MOLTBOOK_CONTROLLED_AUTONOMY=true
MOLTBOOK_EXPERIMENT_STARTED_AT=<ISO-UTC-now>
# Only after a successful dry-run period:
MOLTBOOK_AUTONOMY_DRY_RUN=false
```

Keep `AION_KILL_SWITCH` reachable. Missed targets must never raise limits.

## What this build will not do until you approve

- First autonomous live post/comment/follow
- Enabling controlled autonomy in `.env`
- Expanding permissions
- Any live trading
