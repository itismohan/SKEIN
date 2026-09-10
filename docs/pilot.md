# Skein Pilot Track

The MVP is now treated as the stable local foundation. The Pilot Track measures whether the continuous-thread model produces useful outcomes in a real repository and real agent workflow.

## Local pilot harness

```bash
# Target must already contain a Skein graph at .skein/graph.json
skein pilot-init /path/to/repository --name partner-a --agents 3
skein pilot-run /path/to/repository
skein pilot-report /path/to/repository
```

The harness records:

- raw-context vs targeted graph-context token counts
- duplicate-context reduction across agents
- structural retrieval precision / recall / F1
- local retrieval latency
- graph size and version-history head
- traceability records available to the workspace
- verified-compression evaluation status
- governance controls represented by the MVP

## Interpretation rules

Pilot results are **evidence**, not marketing claims. Whitespace token counts are only a local proxy; provider tokenizer counts and actual model spend must be captured in a design-partner environment.

The harness does not infer LLM answer quality, developer velocity, or production cost savings from structural retrieval alone.

## Design-partner protocol

For each matched workflow, capture:

1. **Context efficiency:** provider input tokens, context reconstruction time, duplicate context calls.
2. **Agent outcome:** task completion, rework, reviewer acceptance, handoff loss.
3. **Engineering flow:** lead/cycle time, review latency, release-readiness effort.
4. **Quality:** defects found before merge, escaped defects, traceability coverage.
5. **Governance:** blocked unsafe writes, policy exceptions, conflicts, audit completeness.
6. **Economics:** model spend per task and cost per successful task.

Run the same scenarios with and without Skein, keep model/agent/task mix fixed where practical, and report the delta rather than a raw absolute number.

## Current deterministic benchmark

The built-in Stage 1 commerce fixture is suitable for validating the harness itself. It contains the existing six structural retrieval questions and provides a reproducible control for regression testing.

A successful local run should not be described as a design-partner pilot. A genuine pilot requires an external repository, real agent traffic, and stakeholder acceptance criteria.
