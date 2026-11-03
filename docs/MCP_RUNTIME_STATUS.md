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
