# Local daily-use runbook

AION is currently a local application stack, not a bootable operating system.
Use the activated virtual environment explicitly; do not rely on a system
`python` command.

## Preflight

Run the passive check before starting services:

```bash
.venv/bin/python scripts/preflight_local.py
```

It does not install dependencies, open microphones/cameras, record audio,
change audio defaults, start services, or print environment values. `missing`
means a local dependency is absent; `unavailable` means a service or passive
device listing did not respond. An occupied runtime port is identified as AION
only when its fixed loopback health response matches; all other occupants,
including Boardroom, are labeled unknown. Never stop or modify an existing
listener from the preflight.

The command exits `0` only when the required local startup checks pass, and
`1` if startup is blocked by a missing dependency, configuration, local model,
or occupied port. Voice checks are reported separately and do not make a
startup-ready host fail: the voice flow is currently unavailable regardless of
prerequisite status.

## Start and stop

Create `.env` and `.env.local` from `.env.example`, keeping secrets private.
For local intelligence, set `AION_RUNTIME_MODE=local` and the owner token in
`.env`; set the matching owner token in `.env.local` for the server-side
Boardroom bridges. In separate terminals:

```bash
.venv/bin/python run.py
npm run dev
```

The runtime defaults to `http://127.0.0.1:8000`; Boardroom runs through the
Next.js app at `http://localhost:3000`. Stop each foreground service with
`Ctrl-C` in its own terminal. Do not use broad process-kill commands.

Check runtime health at `http://127.0.0.1:8000/health` and use the Boardroom
runtime-status surface after owner authentication.

## Verification

```bash
PYTHONPATH=. .venv/bin/python scripts/smoke_owner_audit.py
PYTHONPATH=. .venv/bin/python scripts/smoke_agent_approval.py
```

Both use isolated SQLite data and refuse occupied default ports. Supply
alternative loopback ports when necessary.

## Voice

Voice remains unavailable until the dedicated owner-authorized voice flow is
implemented and configured. The preflight reports passive EMEET discovery,
Whisper/Piper artifacts, Piper executable availability, and the explicit
capture gate. Do not enable capture or test recording unless the owner has
explicitly chosen to do so.
