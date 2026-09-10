# Skein Production Runbook

## Health

```bash
skein health .
```

The command validates the materialized graph against the graph contract, verifies version-history readability, and surfaces persisted optimistic-concurrency conflicts.

## MCP

Expose `/health` for liveness and `/mcp` for JSON-RPC MCP traffic. Supply the authenticated principal as `X-Skein-Identity`; the server resolves that identity to a configured role rather than trusting a caller-supplied role.

## Trust alerts

Treat compression verification failures and incorrect `EXTRACTED`/`INFERRED` provenance as critical quality signals. Do not suppress or aggregate them into generic application errors.

## Release rollback

Use a known-good commit with `skein rollback --to <commit> .`; the rollback itself creates a new append-only commit, preserving audit history.
