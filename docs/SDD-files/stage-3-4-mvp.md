# Skein Stage 3–4 MVP

Stage 3 provides verified compression with a static load-bearing checklist, safe fallback, configurable aggressiveness, and a 120-case release evaluation gate. Stage 4 exposes a lightweight MCP-compatible JSON-RPC server over stdio and HTTP, shared-graph read tools, scoped proposal writes, reviewer-gated commit, and duplicate-context measurement.

## Local MCP
`skein mcp-stdio .`

## HTTP MCP
`skein mcp-http . --host 127.0.0.1 --port 8765`

POST JSON-RPC requests to `/mcp`.

## Compression
`skein compress "..."`
`skein compression-eval`

## Shared-agent flow
Planner proposes -> coder reads shared graph -> coder proposes -> reviewer commits. Proposal commits use the existing SDD commit pipeline and therefore inherit optimistic concurrency, sanity checks, history, and traceability.
