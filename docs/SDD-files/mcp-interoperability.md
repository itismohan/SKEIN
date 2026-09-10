# Skein MCP Interoperability Certification

Skein includes two independent reference adapters to validate that the shared context protocol is not coupled to one agent orchestration style.

## Reference adapters

- **Framework A** — direct tool-call sequencing.
- **Framework B** — message-oriented sequencing through an adapter client.

Both execute a governed graph workflow and commit through the same SDD pipeline.

## Certification command

```bash
skein certify . --output .skein/certification.json
```

The certification report records the framework call sequences, commit identifiers, shared-context measurement, and the deterministic MVP acceptance result.

## Interpretation

This is **offline protocol interoperability evidence**, not certification of commercial agent products. External client validation should be added during a design-partner pilot.
