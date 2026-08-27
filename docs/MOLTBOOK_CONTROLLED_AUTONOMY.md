# Moltbook Controlled Autonomy — 14-day experiment

**Status:** Implemented, **inactive by default**. Awaiting final owner activation approval.  
**Date:** 2026-08-27  
**Does not:** publish live, expand permissions, enable trading, or start the experiment clock automatically.

## Owner authorization summary (accepted)

Authorized during a 14-day controlled-growth experiment (after activation).
Quotas are **ceilings, not targets**. Platform rate limits always override.

| Action | Expanded ceiling | Auto-reduced ceiling |
|--------|------------------|----------------------|
| Original posts | ≤ 2 / rolling 24h | ≤ 1 / rolling 24h |
| Public comments/replies | ≤ 8 / rolling 24h | ≤ 3 / rolling 24h |
| Follows | ≤ 15 / rolling 7d | ≤ 5 / rolling 7d |
| Correct/delete own content | error, privacy, broken link, misleading | same |
| Lead alerts + drafted responses | autonomous identify/score/alert/prepare | same |
| Direct messages | **prohibited** | **prohibited** |
| Pricing, contracts, accepting work | **owner approval required** | same |
| Crypto / wallets / live trading | **prohibited** (paper only ≥ 30 days) | same |

### Mandatory pacing

- ≥ 2 hours between original posts
- ≥ 10 minutes between comments/replies
- ≤ 2 comments in any rolling hour
- ≥ 15 minutes between follows; ≤ 3 follows / hour (no rapid bursts)
- ≤ 2 unsolicited public interactions with the same account / 24h
- Respect Moltbook `Retry-After` / rate-limit responses; platform wins

### Automatic controls

- Semantic duplicate detection, relevance/usefulness scoring, topic diversity
- Reduce to former 1/3/5 on negative feedback, moderation warnings, abnormal failures, or suspicious engagement
- Immediate read-only fallback for platform warnings, credential incidents, or repeated rate-limit responses
- Never auto-increase activity because performance is poor

## Content-generation and qualification rules

Exact machine rules live in `aion/moltbook/autonomy_policy.py` as `CONTENT_GENERATION_RULES` and `qualify_outbound_content()`.

### Posts must

- Be original and non-duplicative (content-hash + idempotency)
- Map to authorized topics (AI-agent safety, building/testing AION, automation, web/tech guidance, ethical collaboration, YaliTek public case studies, technical discussion)
- Be useful without requiring a sale
- Pass secret/PII scanners
- Avoid denylisted financial/crypto/solicitation/contract language
- Be ≥ 40 characters of substantive text

### Comments must

- Be relevant to the specific discussion
- Add a concrete observation, question, resource, or recommendation
- Never be generic praise (`great post`, `interesting insight`, …)
- Ignore instructions embedded in retrieved inbound content (prompt-injection filter)

### Follows must

- Target relevant credible accounts
- Refuse injection/spam heuristics in name or reason

### Leads

Autonomous: identify, score, alert owner, prepare customized response draft.  
Still require owner approval before: email/off-platform move, price quote, consultation offer, requesting customer files/access, accepting work.

Public response OK only when the person states an explicit technical need, a public reply is appropriate, guidance is useful, and any YaliTek mention is transparent and low-pressure.

## Operating controls implemented

| Control | Location |
|---------|----------|
| Global kill switch | `KillSwitch` / `AION_KILL_SWITCH` / owner API |
| Atomic rolling counters | `AutonomyStore.increment_counter` |
| Idempotency keys | `autonomy_actions.idempotency_key` |
| Content hashes + duplicate detection | `content_hash` + `recent_content_hashes` |
| Action/topic allowlists | `AUTHORIZED_ACTIONS`, `TOPIC_ALLOWLIST` |
| Financial/sensitive denylists | `DENYLIST_PATTERNS` |
| Secret + PII scanning | `scan_secrets_and_pii` |
| Prompt-injection filtering | `detect_prompt_injection` + inbound block |
| Audit logs (before/after) | `Phase2Store.append_audit` + autonomy action/block tables |
| Read-only fallback after repeated errors | `AutonomyPolicy.record_error` → `read_only_fallback` |
| Suspension on credential exposure | `suspend_for_credential_exposure` |
| Daily owner report | `ControlledAutonomyEngine.build_daily_report` |

## Environment (defaults keep writes off)

```bash
MOLTBOOK_CONTROLLED_AUTONOMY=false   # must stay false until final approval
MOLTBOOK_AUTONOMY_DRY_RUN=true       # even when active, dry_run blocks network writes
# MOLTBOOK_EXPERIMENT_STARTED_AT=    # set only at activation (ISO UTC)
AION_KILL_SWITCH=false
```

Activation requires **all** of:

1. Guardrails tested (see `tests/test_controlled_autonomy.py`)
2. Owner review of this doc + `CONTENT_GENERATION_RULES`
3. Adversarial tests green
4. Kill switch verified
5. Safety report concludes “ready pending final approval”
6. **Separate** final owner message authorizing activation
7. Then set `MOLTBOOK_CONTROLLED_AUTONOMY=true`, set experiment start, and only then consider `MOLTBOOK_AUTONOMY_DRY_RUN=false`

Missed performance targets must never auto-raise limits.

## Crypto boundary

Urgency does not apply to live trading. Paper trading only for at least 30 days. No wallet, exchange, trading, withdrawal, deposit, leverage, or custody permissions.

## Activation checklist (stop here until owner says go)

- [x] Implement guardrails
- [x] Document exact content/qualification rules
- [x] Adversarial tests for injection, secrets, spam, duplicates, rate limits
- [x] Kill switch confirmation in tests
- [x] Safety report (see PR / agent summary)
- [x] Final owner approval (Yaleel, 2026-08-27)
- [x] Merge PR #17
- [x] Production dry-run verification (all passed)
- [x] Live arm: `MOLTBOOK_AUTONOMY_DRY_RUN=false` + experiment clock started

See `docs/MOLTBOOK_AUTONOMY_ACTIVATION.md` for timestamp, kill-switch procedure, and daily report schedule.
