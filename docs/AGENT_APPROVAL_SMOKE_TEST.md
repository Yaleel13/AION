# Agent approval smoke test

Run the complete local agent approval workflow with:

```bash
PYTHONPATH=. .venv/bin/python scripts/smoke_agent_approval.py
```

The check refuses to run when its loopback runtime port (default `8000`) or
Boardroom port (default `3001`) is occupied. Choose alternatives with
`--runtime-port` and `--boardroom-port`. It starts the services without a
reloader, uses a temporary SQLite database, and stops only the process groups
it created.

## Prerequisites

- Install Python dependencies in `.venv` and frontend dependencies in
  `node_modules`.
- Create `.env` and `.env.local` from `.env.example`.
- Set the same non-empty `AION_OWNER_TOKEN` in both files.

The check generates distinct ephemeral local-agent credentials for its
temporary runtime. It explicitly loads dotenv files but does not print credentials
or validator output. It verifies:

1. Owner MCP discovery exposes only `runtime_status`; agent MCP discovery
   exposes only approval submission and redemption.
2. Agent MCP submission creates one pending request, and pending redemption is
   denied without starting a job.
3. The owner-session, CSRF, and same-origin Boardroom bridge approves that
   exact request.
4. Agent MCP redemption runs the fixed validator once; replay is denied
   without a second job.
5. Owner audit lookup contains the expected policy, job-start, and outcome
   records, and the isolated audit store correlates the approval ID with the
   runtime request ID.
