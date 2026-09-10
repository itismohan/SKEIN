# Contributing to Skein

## Schema is a contract
The graph schema is versioned under `schemas/graph.schema.json`. Any incompatible change requires a schema version bump and a migration plan. Additive, backward-compatible changes must still be reviewed as contract changes.

## Change process
1. Propose the schema change in a PR.
2. Explain compatibility and migration impact.
3. Update validation tests and fixtures.
4. Provide a migration for persisted graphs when required.
5. Update the schema version only when the contract actually changes.
6. CI must remain green before merge.

Do not silently change node or edge semantics in implementation code.
