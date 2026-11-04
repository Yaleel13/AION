# Fixed Local Executive validation

`POST /local-executive/validate` accepts an empty JSON object (`{}`). It requires
the existing owner bearer authorization, a loopback caller, and
`AION_RUNTIME_MODE=local`. It is available on POSIX runtimes only. Extra body
fields and query parameters are rejected. Pass the owner token privately through
the HTTP Authorization header; never store it in source or command history.

The single job, `runtime.syntax`, runs the current Python executable with `-I`
and the server-defined `scripts/validate_runtime_syntax.py` path. It parses the
Python sources in `aion/`, `api/`, and `run.py` without importing them or writing
bytecode. The working directory is fixed to the checkout root. Only `LANG` and
`PYTHONIOENCODING` are passed in the environment; runtime credentials are excluded.

The job has a 30-second deadline covering startup and execution, and retains at
most 12,000 bytes of combined stdout and stderr while continuing to drain both
pipes. Incomplete or invalid UTF-8 is omitted to preserve the byte limit. Results report
`succeeded`, `failed`, `timeout`, or `unavailable`. Cancellation or a disconnected
HTTP caller kills the process group and reaps the direct child before completing
cleanup. A detected disconnect returns HTTP 499 when a response is still possible.
If cancellation or the deadline occurs during startup, the runner retains ownership
of the pending spawn and waits for its handle so it can kill and reap the process
before returning. Cleanup can therefore extend the response beyond the deadline.

No caller controls the executable, arguments, environment, directory, or deadline.
This endpoint does not expose arbitrary shell execution and is not registered in
MCP. Existing Local Executive capability behavior is unchanged.

In the authenticated Boardroom, use **Runtime Validation → Run syntax check**.
The button stays disabled during the request and shows the result or runtime
unavailability. The same-origin `/api/owner/runtime/syntax` bridge checks the
existing owner session, CSRF header, and Origin before forwarding the fixed empty
request to the loopback runtime. The owner bearer token stays on the server.

After the existing endpoint gates pass, shared capability dispatch resolves
`runtime.syntax` with the existing `execute` action and checks its pure catalog
permission before invoking the async validator. Policy denial returns 403 and
policy evaluation failure returns a redacted 503; neither starts a process.
The async adapter directly awaits the existing runner so timeout, task
cancellation, and disconnect cleanup keep their existing behavior and response
contract. The live capability registry reports this job eligible only on a local
POSIX runtime with owner authentication configured; the stable catalog describes
the installed job's permission ceiling. This does not register an MCP tool.

See [runtime capability audit](CAPABILITY_AUDIT.md) for request correlation,
policy/start/outcome events, privacy rules, and audit storage limitations.

## Internal syntax approval claims

The durable `runtime_syntax_approvals` table is an internal storage primitive
for a future agent-request and owner-approval flow. It issues a server-generated
execution request ID bound to the fixed `runtime.syntax` capability and a trusted
requester principal. Owner decisions expire, and a claim is a single conditional
database update that requires the exact ID, capability, requester, approved
state, unexpired time, and an unconsumed row.

Claim success is reported only after commit. Storage failures deny the claim.
A committed claim is spent even if a later syntax launch fails, so a failed
launch must not be retried with the same approval. This storage primitive does
not claim or launch syntax validation, and it does not change MCP exposure.

## Local agent approval requests

Set distinct `AION_LOCAL_AGENT_TOKEN` and `AION_LOCAL_AGENT_PRINCIPAL` values
only in local runtime configuration to enable `POST
/agent/runtime-syntax-approvals`. The endpoint accepts an empty JSON object,
uses the configured principal rather than caller input, and is loopback-only.
The owner token is explicitly rejected there.

Boardroom uses the session-authenticated owner bridge at
`/api/owner/runtime/syntax/approvals/{execution_request_id}` to review an exact
request and post its single owner decision. That bridge requires the existing
owner session, CSRF header, and same-origin check. Agent credentials are
rejected by the runtime owner endpoints. These paths only create and decide
approvals; they do not claim or launch syntax validation, and MCP remains
read-only with only `runtime_status`.

## Local agent approval redemption

The local agent redeems an approved request with an empty JSON object at `POST
/agent/runtime-syntax-approvals/{execution_request_id}/redeem`. The path ID
must be the server-issued 32-character request ID; query parameters and
caller-supplied capability, principal, execution, or audit fields are rejected.
The runtime derives the requester from the verified local agent credential,
checks the fixed `runtime.syntax` capability policy, then atomically claims the
approval from local SQLite before starting the fixed validator. Other database
backends are rejected until they have equivalent redemption integration
coverage.

The claim is irreversible even if process startup fails or the caller
disconnects. Audit records attach the approval request ID to the runtime's
server-generated request ID without recording credentials or validation output.
