# Skein MCP Reference

Skein exposes a lightweight JSON-RPC MCP-compatible server over stdio and HTTP.

## Read tools

- `query_graph`
- `get_subgraph`
- `get_traceability`
- `get_diff`

## Proposal/write tools

- `propose_node`
- `propose_edge`
- `commit_proposal`

Writes are proposal-first. A reviewer/admin identity is required to commit. Identity is resolved from the workspace policy; callers must not elevate themselves by supplying a role.

### Identity policy

Configure `.skein/mcp-policy.json` using `.skein-mcp-policy.example.json`. HTTP clients should send `X-Skein-Identity`; stdio integrations may pass an `identity` field.

## Protocol

The MVP supports JSON-RPC 2.0 `initialize`, `tools/list`, and `tools/call`. `notifications/initialized` is accepted as a notification and produces no response.
