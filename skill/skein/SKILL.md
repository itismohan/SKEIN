# Skein — Shared Engineering Context Skill

Use Skein as the persistent context layer for AI-DLC work.

## Operating rules

1. Query the Skein graph before reconstructing repository context from raw files.
2. Use traceability queries when a requirement, ticket, ADR, test, or commit must be justified.
3. Treat `EXTRACTED` and `INFERRED` edges differently; never silently upgrade inferred evidence.
4. Propose graph writes before committing them. Reviewer-authorized commits must pass the SDD commit pipeline.
5. Use verified compression for context reduction. If verification fails, retain the uncompressed context.
6. Prefer structural diffs and version history when explaining what changed.
7. Do not execute subprocesses or network operations unless the active Skein sandbox policy explicitly allows them.

## Preferred workflow

`query_graph → get_subgraph → get_traceability → propose_node/propose_edge → reviewer commit → diff → audit`

## Trust-sensitive failures

Escalate immediately when:
- compression drops a required error, security control, command, or edge case;
- an `EXTRACTED` / `INFERRED` provenance label appears incorrect;
- a write conflicts with a newer graph version.


## v0.5 Evaluation

Use `skein evaluation-init`, `skein evaluate`, and `skein evaluation-report` for matched-task statistical evidence. Do not claim causal impact from bootstrap intervals alone.

## v0.6 Experimental Control Plane

Use `skein experiment-init`, `skein experiment-add-task`, `skein experiment-assign`, `skein experiment-status`, and `skein experiment-verify` to establish reproducible study provenance. Treat confounds as explicit evidence gaps. Randomization and a valid manifest do not establish causal impact without matched execution telemetry and quality guardrails.


## v0.7 Real Agent Execution

Use `skein agent-run` only with an explicit JSON argv command and a task assignment produced by the v0.6 experiment control plane. The runtime captures outcome, latency, context fingerprints, and normalized connector telemetry. It uses `shell=False`; do not bypass the execution environment's sandbox or network policy.
