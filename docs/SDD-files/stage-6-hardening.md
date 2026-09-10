# Stage 6 — Hardening & Release Certification

Skein `0.2.0` is an **MVP Release Candidate**, not a claim of production certification.

## Offline acceptance gate

Run:

```bash
pytest
skein release-check .
skein acceptance . --output .skein/acceptance.json
```

The acceptance suite covers versioned ingestion, verified compression preservation, the compression evaluation corpus, governed MCP writes, shared-context measurement, and the sandbox boundary.

## External gates

The following require evidence outside the local build environment:

- publication to PyPI and npm;
- a closed design-partner pilot on production repositories;
- measured token reduction and duplicate-call reduction during that pilot;
- zero measured compression accuracy regression against the agreed pilot baseline;
- live uptime/health monitoring and alert routing;
- independent security/compliance review.

These must remain explicitly marked **not evidenced** until executed.

## Trust-risk feedback

Report two failure classes separately from ordinary bugs:

1. compression false negatives — required error/security/edge-case information lost;
2. incorrect `EXTRACTED` / `INFERRED` provenance tagging.

Both are release-blocking trust defects until triaged and verified.

## Final integrity verification

Skein now exposes `skein verify` to validate the append-only graph history. The verifier checks deterministic commit IDs, parent continuity, delta replay, graph schema validity, materialized-state equivalence, and history/state head agreement. This is a local integrity control; it does not replace cryptographic signing, remote WORM storage, or an external trust anchor.
