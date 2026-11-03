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
