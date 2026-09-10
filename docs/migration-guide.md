# Migration Guide

## From pre-versioned Skein workspaces

Run:

```bash
skein migrate .
```

The command preserves the materialized graph and creates an append-only history with an explicit migration commit.

## From standalone compression

Compression remains callable through `skein compress`. Existing text is never modified in place. Verification failure returns the original input as the safe fallback.

## From direct graph writes

Prefer `skein commit-graph` or the MCP proposal/commit workflow. Direct edits to `.skein/graph.json` are treated as a materialized-state operation and should be followed by validation and a versioned commit.
