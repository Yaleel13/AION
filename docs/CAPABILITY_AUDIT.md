# Runtime capability audit

The existing Phase 2 owner audit history (`audit_history` in the owner dashboard)
now includes module `capabilities` for `/runtime/status`,
`/owner/runtime/status`, and `/local-executive/validate`. It uses the existing
`Phase2Store.append_audit` sink and schema; no database migration is required.

Each HTTP request receives a server-generated `X-AION-Request-ID` response header.
The same ID appears in every related audit row's `detail.request_id`, alongside
the fixed capability, permission, method, path, policy decision, and job-started
flag. Caller-supplied IDs are ignored. Concurrent requests have separate IDs.

- `capability.policy`: `allowed`, `denied`, or `unavailable` (policy failure).
- `capability.job_started`: emitted only when the fixed syntax subprocess handle
  has been acquired, including acquisition during startup cancellation cleanup.
  Permission alone never produces this event. Status reads have no job start.
- `capability.outcome`: `succeeded`, `failed`, `timeout`, `unavailable`,
  `cancelled`, `denied`, `policy_unavailable`, or `rejected`, plus HTTP status.
  Syntax outcomes are recorded after the endpoint has drained its tasks and
  completed process cleanup. Authentication/body/transport rejection records
  `policy_decision: not_evaluated` and `job_started: false`.

Rows never include tokens, request bodies, query values, subprocess output,
exception messages, or status snapshot contents. Cancellation before response
headers can leave the recorded HTTP status at 500; the explicit `cancelled`
outcome is authoritative, since no HTTP response was sent.

Audit persistence is best effort: sink failure emits a generic warning without
exception details and does not change diagnostic responses or process cleanup.
Failure of the warning's logging handler is also contained. Each HTTP request
attempts exactly one terminal outcome write; a failed sink write is not retried
or claimed as durable evidence.
An unavailable sink therefore leaves a durable evidence gap. A process crash
can also leave a policy/start event without a final outcome. No crash recovery
or new audit viewer is introduced here. The Boardroom syntax bridge forwards
only a validated `X-AION-Request-ID` (exactly 32 lowercase hex characters) and
shows it beside the result. The stdio status tool exposes the same validated ID
in result `_meta["aion/request_id"]`, without modifying content or the status
payload. Both retain references on runtime error responses and omit them when
the header is missing, invalid, or the runtime cannot be reached. Caller IDs and
all other upstream headers are excluded; a new Boardroom run clears the old ID.
MCP preflight rejection or an unreachable runtime never reaches this HTTP audit
boundary. MCP discovery remains limited to `runtime_status`.
