# Stage 2 — SDD Foundation + Versioned Graph Store

Stage 2 begins with an executable Spec-Driven Development boundary. Machine-readable clauses in `spec/clauses/` define what the implementation is allowed to claim. Tier A clauses require evidence and executable tests; Tier B clauses require a review date, success metric, and validation plan; Tier C clauses are quarantined. This follows the Spec Factory trust model. 

The versioned graph is an append-only commit history. Every accepted mutation records a deterministic commit identifier, parent version, timestamp, author, message, spec references, and a structural delta. The materialized graph is derived from that history and persisted separately for fast reads.

## SDD → implementation contract

```text
Spec Clause → Evidence → Test → Implementation → Commit → Trace
```

Every Stage 2 implementation PR must:

1. reference at least one SDD clause;
2. add/update executable evidence for changed Tier A behavior;
3. keep Tier B hypotheses time-boxed;
4. produce an append-only graph commit;
5. expose structural diff evidence;
6. reject stale writes using optimistic concurrency.

## Current foundation

- `skein/sdd/`: machine-readable clause model and validator.
- `skein/versioning.py`: append-only commit log, materialized state, diffing, rollback, optimistic concurrency.
- `spec/clauses/`: Stage 2 contracts SKN-001 through SKN-003.
- `ci/check_spec_drift.py`: CI trust-tier gate.
- `tests/unit/test_stage2_versioning.py`: executable evidence for commit, diff, confidence change, and stale-write behavior.

## Next increments

1. PR structural diff reporter.
2. persisted conflict records and conflict inspection CLI.
3. stronger rollback/sanity-check semantics.
4. `since` / date-range history queries.
5. ingestion and agent writes routed exclusively through the versioned commit API.
6. SDD traceability graph linking clauses ↔ tests ↔ commits ↔ affected nodes/edges.
