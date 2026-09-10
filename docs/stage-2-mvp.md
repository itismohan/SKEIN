# Skein Stage 2 MVP

Stage 2 makes graph history an SDD-governed engineering artifact. The MVP closes the loop from repository ingestion through versioned graph commits, structural diff, traceability, sanity checks, rollback, concurrency conflicts, and CI reporting.

## Core flow

`Repository -> Ingestion -> Working Graph -> SDD Validation -> Graph Commit -> Delta History -> Diff -> Traceability -> Sanity -> Report`

## Commands

```bash
skein ingest .
skein history .
skein history . --since <commit-id>
skein history . --since-date 2026-09-10T00:00:00+00:00
skein diff . --from <base> --to <head>
skein trace . --spec SKN-004
skein conflicts .
skein pr-report . --base <base> --head <head> --output skein-pr-report.md
skein rollback . --to <known-good-commit>
```

## SDD rule

Accepted graph mutations require an active non-Tier-C clause. Tier-A clauses require executable evidence. Ingestion is governed by `SKN-004`.

## MVP acceptance

- Every changed ingestion produces a graph commit before `graph.json` is published.
- Unchanged ingestion produces no empty commit.
- Commit history is append-only and queryable.
- Structural diff reports node/edge additions, removals, modifications and confidence changes.
- Stale writes are rejected and persisted in `conflicts.jsonl`.
- Post-write sanity checks reject invalid/orphaned graph states.
- Rollback creates a new commit restoring a known-good state.
- PR report is reproducible from base/head graph versions.
- Rapid sequential writes are exercised by a 100-commit load test.
