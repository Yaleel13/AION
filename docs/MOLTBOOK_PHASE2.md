# Moltbook Phase 2 — Threat Model & Controlled Growth

**Status:** Draft implementation (no autonomous publish / no live trading)  
**Date:** 2026-08-27  
**Depends on:** Phase 1 read-only foundation (`docs/MOLTBOOK_PHASE1.md`)

## Objectives

1. Grow AION’s reputation through useful, original contributions.
2. Discover legitimate YaliTek service opportunities from **public** Moltbook content.
3. Measure whether Moltbook yields qualified leads or revenue.
4. Run an isolated crypto **paper-trading** experiment (BTC/ETH only).
5. Preserve **human approval for every public or financial action**.

## Trust boundaries

| Domain | Trust | May auto-execute? |
|--------|-------|-------------------|
| Owner instructions (chat / explicit approval) | Trusted | Yes, within approved scope |
| Repository constitution / Phase rules | Trusted | N/A |
| Moltbook posts, comments, profiles, DMs | **Untrusted** | Never as instructions |
| Public market data APIs | Untrusted data | Simulation only |
| Lead enrichment / third-party identity APIs | Forbidden in Phase 2 | No |

Retrieved Moltbook content **must never**:

- Override system/developer instructions
- Trigger tools or shell commands by itself
- Authorize outbound or financial actions
- Request or reveal secrets
- Become trusted memory without owner review

## Assets to protect

- `MOLTBOOK_API_KEY` and any future credentials
- Owner approval tokens
- Customer / confidential YaliTek data (must never enter Moltbook drafts)
- Paper-trading state (must not be confused with real funds)
- Audit integrity

## Adversaries / failure modes

1. **Prompt injection** via feed/search content instructing AION to post, follow, or leak keys.
2. **Approval replay** — reuse of an old approval for different content/destination.
3. **Content drift** — approved draft silently edited then published.
4. **Engagement farming / spam** — exceeding community norms or platform rules.
5. **False leads** — treating generic discussion as qualified demand.
6. **Paper→live confusion** — treating simulation returns as expected profit or wiring live keys.
7. **Secret leakage** into logs, git, client bundles, or dashboard responses.

## Controls (Phase 2)

- Single-use approval tokens bound to **action + destination + content hash**
- Approval expiry (default 24h)
- Invalidation if content or destination changes
- Kill switch → emergency read-only
- Daily/weekly outbound quotas (stricter than platform limits)
- Duplicate-content detection
- Prompt-injection heuristics on inbound text
- Redacted immutable audit log (append-only SQLite + optional JSONL)
- Idempotency keys on propose/execute
- Module separation: `moltbook` / `leads` / `paper_trading`
- Owner dashboard requires `AION_OWNER_TOKEN` (server-side only)
- Paper trading: virtual capital only; no exchange trading keys; BTC+ETH only; 30-day minimum before any live proposal

## Platform constraints (Moltbook rules, Aug 2026)

Respect official limits and rules (`https://www.moltbook.com/rules.md`, `skill.md`):

- Quality over quantity; no karma farming / mass follow
- New-agent stricter cooldowns in first 24h
- Posts: platform ~1 / 30 min (established); Phase 2 owner ceiling: **2 original posts / 24h** (≥2h apart); auto-reduces to 1
- Comments: Phase 2 owner ceiling: **8 / 24h** (≥10 min apart, ≤2 / hour); auto-reduces to 3
- Follows: Phase 2 owner ceiling: **15 / week** (no rapid bursts); auto-reduces to 5
- No unsolicited DMs in Phase 2 policy (platform may allow DMs after 24h)
- Platform rate limits always override owner ceilings; quotas are ceilings, not targets

## Explicitly out of scope for this PR

- Publishing, commenting, following, or messaging without separate owner approval tokens consumed by an executor
- Merging/deploying production secrets
- Live exchange connectivity, wallets, leverage, deposits/withdrawals
- Automatic responses driven solely by retrieved content

See also: `docs/MOLTBOOK_CONTROLLED_AUTONOMY.md` for the 14-day experiment guardrails
(still inactive until final owner activation).

## Rollback

1. Set kill switch / `MOLTBOOK_PHASE2_OUTBOUND=false` / `MOLTBOOK_CONTROLLED_AUTONOMY=false`
2. Revert to Phase 1 client usage (`MOLTBOOK_MODE=mock|live` read-only)
3. Delete or ignore Phase 2 SQLite DB path
