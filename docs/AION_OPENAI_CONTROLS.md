# AION OpenAI Provider Controls

**Status:** Implemented  
**Primary provider:** OpenAI only (Gemini not configured as primary)

## Defaults

| Control | Default |
|---------|---------|
| Model allowlist | `gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`, `gpt-4.1`, `o4-mini` |
| Default model | `gpt-4o-mini` (`AION_MODEL`) |
| Max input tokens | 4000 |
| Max output tokens | 1200 |
| Daily cost ceiling | **$5.00 USD** (`AION_OPENAI_DAILY_COST_USD`) |
| Timeout | 45s |
| Retries | 2 |

## Behavior

- Scrub secret-looking material before send
- Block private founder context / injection patterns → safe non-LLM fallback
- Log usage + estimated cost to `$AION_DATA_DIR/openai_usage.db`
- On API failure or ceiling → fallback response (no crash)

## Secrets

- `OPENAI_API_KEY` — server-side only
- Never send owner token, private repos, customer info, or `OWNER_PRIVATE_CONTEXT` to the model

## Cost

- Ceiling **$5/day** estimated (soft stop)
- Expected monthly: depends on usage; start with real key + monitor

## Blocker

Current environment `OPENAI_API_KEY` appears to be a **placeholder**. Owner must set a real server-side key before live LLM calls succeed.

## Rollback

Unset `OPENAI_API_KEY` or set `AION_OPENAI_DAILY_COST_USD=0` to force fallback mode.
