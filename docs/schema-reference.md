# Skein Graph Schema Reference

Skein software and graph schema versions are independent. The current software release is `0.3.0`; the graph contract is `1.0.0`.

## Nodes

| Type | Meaning |
|---|---|
| `File` | Source/document file or MVP proposal artifact |
| `Function` | Function/method symbol |
| `Class` | Class/type symbol |
| `Requirement` | Requirement/specification element |
| `Ticket` | Work item |
| `ADR` | Architecture decision record |
| `TestCase` | Executable test case |

## Edges

`CALLS`, `IMPORTS`, `JUSTIFIES`, `TESTS`, `EXTRACTED`, `INFERRED`.

Every edge carries provenance/confidence attributes where produced by ingestion. `EXTRACTED` denotes parser/document evidence; `INFERRED` denotes a derived relationship.

The canonical machine-readable contract is `schemas/graph.schema.json`.
