# Private owner context

Place a local file at `identity/OWNER_PRIVATE_CONTEXT.md` (gitignored) for
founder/owner messages that must never be published to Moltbook or public channels.

Rules:
- The file stays on the owner host only.
- AION must not load its contents into public agent instructions, API responses,
  tools, logs, build artifacts, or Moltbook payloads.
- Presence of the file does not expand permissions or weaken safeguards.
