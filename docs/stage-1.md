# Skein Stage 1 — Ingestion & Graph Construction

Stage 1 converts source code and surrounding engineering documents into Skein's structural graph. It follows the uploaded Stage 1 specification: parser plugins, first-class EXTRACTED/INFERRED confidence, community detection, document extraction, linkage heuristics, incremental hashing, watch mode, git hook integration, benchmarking, and graph query.

## Commands

```bash
skein init .
skein ingest .
skein query "what calls calculate_total?" .
skein communities .
skein watch .
skein install-hook .
```

Use `skein ingest . --full-rebuild` when a complete rebuild is intentionally required.

## Parser architecture

`ParserPlugin` is the extension point. Python, JavaScript and TypeScript Tree-sitter adapters are used when their grammar packages are installed. The development environment also has dependency-free conservative fallbacks so Stage 1 can be exercised before optional parser wheels are available.

## Provenance

Every relationship has `attributes.confidence` set to `EXTRACTED` or `INFERRED` at creation time. Direct imports and resolvable direct calls are `EXTRACTED`; document references and ID-based linkage are `INFERRED`.

## Incrementality

`.skein/manifest.json` stores SHA-256 content hashes. Unchanged files are skipped. Changed/removed files have their owned file/function/class/document region removed and rebuilt.

## Community detection

The local implementation uses NetworkX greedy modularity over CALLS/IMPORTS edges as the modularity-based equivalent available without an additional Leiden dependency. The return structure is intentionally an adapter boundary for a future Leiden hierarchy.

## LLM document extraction

`DocumentExtractor` is the provider boundary. The current offline implementation is conservative and deterministic: it creates Requirement/Ticket/ADR candidates and INFERRED reference links. A future LLM provider can implement the same interface without changing ingestion or storage.

## Exit criteria status

- End-to-end ingestion: implemented and tested.
- Reproducible benchmark harness: implemented; run against a fixed internal repository before claiming a measured token reduction.
- Incremental subgraph update: implemented and covered by tests.
