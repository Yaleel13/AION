# Moltbook Secure Local Configuration

This guide covers **owner-only** setup for Phase 1 read-only access. It does not
register the agent for you and does not enable posting.

## Threat model (Phase 1)

- Secret: `MOLTBOOK_API_KEY`
- Allowed live calls after you configure the key: **status**, **profile**, **limited feed**
- Blocked: post, comment, follow, subscribe, vote, register, profile update, messaging, spend
- All retrieved Moltbook content is **untrusted data** (never instructions)

## Prerequisites

1. PR / branch with the Phase 1 package (`aion/moltbook/`) available locally.
2. Python 3.11+ with project dependencies (`pip install -r requirements.txt`).
3. A private place to store secrets (password manager or OS keychain). Git is not that place.

## Manual registration and claim (you do this)

Do these steps yourself on Moltbook. Do not paste the API key into chat, tickets, or commits.

1. Register (one-time):

```bash
curl -X POST https://www.moltbook.com/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "AION", "description": "Alchemical Intelligence for Ontological Navigation — mentor, research partner, and systems thinker."}'
```

If `AION` is taken, try `AION_Navigator` then `AION_Emissary` (see `identity/MOLTBOOK_EMISSARY.md`).

2. Immediately copy `agent.api_key` from the response into your password manager.
   The key is shown once and cannot be recovered from the API later (owner dashboard rotation is the recovery path).
3. Open `claim_url` in a browser and complete email + ownership verification (verification tweet / claim flow).
4. Confirm claim status later with the verify script (below), not by pasting the key into chat.

Official reference: https://www.moltbook.com/skill.md

## Create a private local `.env`

`.env` is gitignored (including `.env.local`, `.env.*` variants). `.env.example` is the only committed template.

```bash
cp .env.example .env
chmod 600 .env
```

Edit `.env` locally (editor or password-manager fill). Set:

```env
MOLTBOOK_MODE=live
MOLTBOOK_API_KEY=<paste-from-password-manager>
MOLTBOOK_BASE_URL=https://www.moltbook.com/api/v1
MOLTBOOK_OUTBOUND_ENABLED=false
```

Rules:

- Never put the real key in `.env.example`, docs, tests, PR descriptions, or shell history if you can avoid it.
- Never prefix Moltbook secrets with `NEXT_PUBLIC_` (that would expose them to the browser bundle).
- Never commit `.env`. Verify with: `git check-ignore -v .env`
- Prefer `chmod 600 .env` on multi-user machines.

## Confirm secrets cannot enter Git or the Next.js client bundle

```bash
# Must report that .env is ignored
git check-ignore -v .env .env.local

# Must print nothing (no tracked secret env files)
git ls-files | rg -i '(^|/)\\.env($|\\.)|credentials\\.json' || true

# Moltbook is Python-server only; frontend must not import it
rg -n "moltbook|MOLTBOOK_" app components lib --glob '*.{ts,tsx,js,jsx}' || true
```

Expected: ignore hits for `.env*`, no tracked secret files, no frontend Moltbook imports.

## Safe verification command (no key on the CLI)

After `.env` is configured **or** while still in mock mode:

```bash
# Mock (no key required) — run anytime
MOLTBOOK_MODE=mock python3 scripts/moltbook_readonly_verify.py

# Live read-only — uses key from private .env only (after you configure it)
python3 scripts/moltbook_readonly_verify.py
```

The script:

- loads `.env` via python-dotenv
- calls **status**, **profile**, and a **5-item feed** sample only
- prints redacted summaries (never the API key)
- attempts `create_post` and asserts it is blocked

If credentials are not ready, use the mock command only.

## Rollback

1. Set `MOLTBOOK_MODE=mock` or delete the key line from `.env`.
2. Optionally remove `.env` entirely.
3. Rotate the key from the Moltbook owner dashboard if exposure is suspected.

## What still requires explicit owner approval

- Merging the Phase 1 PR
- Enabling any outbound / write action
- Wiring Moltbook tools into the AION agent runtime
- Production deployment of live credentials
- Promoting any Moltbook content into trusted AION memory
