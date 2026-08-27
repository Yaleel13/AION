# YaliTek Knowledge Integration

**Status:** Draft document ready for owner review — **not active**  
**PR:** E

## Canonical document

See [`YALITEK_CANONICAL_KNOWLEDGE.md`](./YALITEK_CANONICAL_KNOWLEDGE.md).

AION will **not** rely on it until:

```bash
AION_YALITEK_KNOWLEDGE_APPROVED=true
```

## GitHub App — verified before use

| Item | Current value |
|------|----------------|
| Installation repos | `Yaleel13/AION` **only** |
| YaliTek Online repo | **Not installed / not visible** |
| Requested permissions | Contents: Read, Metadata: Read |
| Forbidden | Write, admin, actions, secrets, deployments, webhooks, org-wide, Elaria, Cerebral Synergy |

**Owner must** add the exact YaliTek Online repository to the App with read-only Contents+Metadata, then set:

```bash
AION_YALITEK_GITHUB_REPO=Yaleel13/<exact-repo-name>
```

Do not clone or ingest until scope is re-verified and reported.

## Ingest rules

- Allowlist: `docs/**/*.md`, `README.md`, `public/**/*.md`
- Deny: credentials, customer records, private/security paths, wallets/keys

## Threat assessment

| Threat | Mitigation |
|--------|------------|
| Using draft prices | Approval gate |
| Over-broad GitHub access | Scope verification; Contents/Metadata only |
| Secret ingest | Path denylist |
