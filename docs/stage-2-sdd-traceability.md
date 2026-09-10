# Stage 2 — SDD Traceability + Commit Pipeline

The commit path is now SDD-governed. An accepted graph mutation must name at least one active SDD clause. The pipeline validates the clause, creates the graph commit, then appends traceability links.

Canonical trace:

```text
Spec Clause ──PROVEN_BY──> Test
     │
     └──IMPLEMENTED_BY──> Commit ──AFFECTS──> Graph Node / Edge
```

## Pipeline

1. Load and validate `spec/clauses/*.yaml`.
2. Require one or more `spec_refs`.
3. Reject unknown clauses and active Tier C clauses.
4. Require executable evidence for Tier A.
5. Commit through `VersionedGraphStore`.
6. Append immutable trace links to `.skein/history/trace.jsonl`.
7. Expose links with `skein trace --spec SKN-001` or `skein trace --commit <id>`.

This keeps the SDD playbook's rule that tests are the living, checkable form of the specification and makes the graph history itself evidence-bearing.
