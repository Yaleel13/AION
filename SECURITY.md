# AION Security Policy

AION is a public repository. Treat all repository contents, commit history, pull requests, issues, logs, and build metadata as publicly visible.

## Secrets

Never commit credentials, private keys, bearer tokens, database passwords, webhook secrets, API keys, service-role keys, session cookies, or private covenant material.

Secrets must live only in approved secret stores such as Vercel environment variables, Supabase project secrets, or GitHub Actions secrets. `.env.example` must contain placeholders only.

If a secret is exposed, rotate it immediately at the provider, invalidate dependent sessions/tokens, remove it from current files, and review Git history and logs for exposure. Do not rely on deleting the latest commit alone.

## High-risk surfaces

Changes touching authentication, owner-only routes, database access, outbound agent actions, Moltbook, billing/Stripe, external webhooks, GitHub write access, or production deployment controls require explicit owner review.

Owner-only server routes must fail closed when owner authentication is missing or invalid. Sensitive values must remain server-side and must never be returned to the browser or logs.

## Autonomy boundaries

AION must not gain unrestricted authority over live funds, wallets, exchanges, withdrawals, leverage, or external account ownership through ordinary code changes. Paper-trading and simulated finance paths must remain clearly separated from live financial actions unless a separately reviewed and explicitly approved security design is introduced.

## Dependency hygiene

Dependabot is configured for npm and pip. Security and dependency update pull requests should be reviewed promptly. Avoid unbounded dependency ranges where practical; prefer lockfiles or reproducible constraints for production paths.

## Reporting

Do not open a public issue containing an active secret or exploitable private detail. Rotate the affected credential first, then record a sanitized incident summary and remediation steps.
