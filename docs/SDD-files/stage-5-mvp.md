# Skein Stage 5 MVP — Dashboard & Governance

Stage 5 adds the operational control plane around the graph, trace, compression, and MCP layers.

## Implemented

- Append-only agent-call token/cost telemetry in `.skein/history/agent_calls.jsonl`.
- Lifecycle-stage attribution for MCP calls: design, code, review, test.
- Compression verification telemetry in `.skein/history/compression_verification.jsonl`.
- Self-contained governance dashboard: `skein dashboard . --output .skein/dashboard.html`.
- Cost-by-stage, commit/diff history, compression health, and conflict visibility.
- Exportable Markdown audit report combining traceability, structural diff, and compression verification logs.
- Identity-based MCP authorization using `.skein/mcp-policy.json`; HTTP identity can be supplied through `X-Skein-Identity`.
- Conservative sandbox boundary: repository path confinement; subprocess/network execution denied by default.
- Alerting hook for cost spikes, compression fallback rates, and write conflicts.

## Security posture

The MVP intentionally defaults to deny for subprocess and network execution. The policy layer separates identity from role permissions. This is an implementation boundary, not a claim of production security certification; a formal security review remains required before pilot/production use.

## Commands

```bash
skein dashboard .
skein telemetry .
skein compression-health .
skein audit-report . --commit <commit-id> --output audit.md
skein alerts .
skein sandbox-check .
```

## Acceptance evidence

The automated test suite covers telemetry aggregation, compression health, dashboard/audit rendering, sandbox path enforcement, and identity-scoped MCP authorization.
