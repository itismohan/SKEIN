# Skein Specification-Driven Development

`spec/clauses/` is the machine-readable contract for future Skein stages.

## Trust model

- **Tier A — Corroborated:** load-bearing and executable; must have evidence and a test reference.
- **Tier B — Plausible but uncorroborated:** explicitly time-boxed hypothesis; must have a review date, success metric, and validation plan.
- **Tier C — Contradicted or ambiguous:** must be quarantined and resolved before becoming active specification.

Every clause carries provenance through `origin`, `tier`, and `evidence`. This follows the Spec Factory playbook's core rule that provenance travels with the clause through later stages. fileciteturn8file5L1-L10

## Workflow for each next-stage increment

1. Write or update clauses before implementation.
2. Classify every clause A/B/C.
3. Link Tier A clauses to executable tests.
4. Give Tier B clauses an explicit review date, success metric, and validation plan.
5. Keep Tier C out of `spec/clauses/`; quarantine it instead.
6. Implement only within the clause's verified blast radius.
7. Run the spec gate and tests in CI.
8. Promote B → A only after evidence and tests support the clause.

The intended end state is a living specification that is machine-readable, executable, semantically connected, and authoritative for the engineering lifecycle. fileciteturn8file14L1-L6
