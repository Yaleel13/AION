# Read-only runtime status over MCP

Start the local FastAPI runtime on port 8000 with `AION_OWNER_TOKEN` configured.
Launch the stdio MCP server from the checkout with:

```bash
.venv/bin/python -m aion.mcp_server
```

Supply the same `AION_OWNER_TOKEN` through the MCP host's environment configuration;
never put it in tool arguments. The server does not load dotenv files itself.
It uses the installed [official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/).

The only tool, `runtime_status`, takes no arguments. It performs a fixed GET to
`http://127.0.0.1:8000/owner/runtime/status`, which applies the existing runtime
owner-token policy and delegates to the existing runtime status handler. It
returns the non-secret status snapshot as structured MCP content. Authorization
failure and disconnection return MCP tool errors without a fabricated snapshot.
The HTTP timeout is five seconds; proxies and redirects are disabled.

This bridge exposes no shell, executor, mutation tools, or network listener.
Existing browser WebMCP tools remain separate.

The HTTP status handler now calls the shared `dispatch_capability("runtime_status")`
path in `aion.capabilities`. It checks the existing capability catalog's
`configured` and `read` permissions before invoking the status builder. The
public status route and the owner-protected route share this dispatch path;
the latter still checks the existing owner token first. The stdio tool retains
its fixed HTTP transport, argument-free name, status payload, and MCP error
contract. It does not import the runtime registry or load dotenv files.

Status dispatch has an explicitly registered read handler. Unknown names, unsupported
actions, and denied catalog entries raise a structured-code dispatch exception
without running the handler. Catalog membership does not enable a dispatcher
handler. The fixed `runtime.syntax` HTTP job now uses the same resolver through
an async adapter with the `execute` permission, but remains absent from MCP.

The underlying runtime HTTP request is recorded in the existing owner audit
history; see [runtime capability audit](CAPABILITY_AUDIT.md). The MCP payload
contract remains unchanged and does not expose the HTTP correlation header.

Resolution order is fixed-name lookup, allowed-action check, pure catalog
permission evaluation, then handler invocation. Missing or malformed permission
entries deny with 403. A catalog evaluation failure or invalid catalog structure
fails closed with a generic 503 and never invokes the handler or exposes policy
exception details. The stdio adapter preserves its existing structured tool error
for these denials and for runtime disconnection.
