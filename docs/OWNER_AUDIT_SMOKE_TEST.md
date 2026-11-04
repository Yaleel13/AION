# Owner audit smoke test

Run the end-to-end local Boardroom and MCP audit check with:

```bash
PYTHONPATH=. .venv/bin/python scripts/smoke_owner_audit.py
```

The check starts a fresh loopback runtime on port 8000 and a Boardroom dev
server on port 3001. It refuses to run if either port is occupied; use
`--runtime-port` and `--boardroom-port` to select two free ports. It starts the
runtime without the development reloader so it can stop only the process groups
it starts.

## Prerequisites

- Install Python dependencies in `.venv` and frontend dependencies in
  `node_modules`.
- Create `.env` and `.env.local` from `.env.example`.
- Set the same non-empty `AION_OWNER_TOKEN` in both files. The check loads each
  file explicitly and never prints credentials.

The check creates an owner session, runs the fixed Boardroom syntax job, and
verifies its matching `policy`, `job_started`, and successful `outcome` audit
records. It then launches the configured stdio MCP server through the installed
SDK, verifies discovery contains only `runtime_status`, and verifies that the
tool's metadata request ID matches its `runtime_status` audit records.
