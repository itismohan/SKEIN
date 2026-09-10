# Stage 0 — Project Setup & Scaffolding

Stage 0 follows the uploaded Skein specification: monorepo structure, Python ingestion foundation, TypeScript/Node MCP boundary, storage-agnostic graph adapter, versioned schema-as-contract, and CI from commit one.

The executable Stage 0 implementation currently establishes the Python core and contract. The empty package directories for ingestion, compression, MCP server, dashboard, and evaluation are intentional scaffolding for later stages.

## Exit criteria status

- Versioned schema: **implemented** (`v1.0.0`)
- Schema validation: **implemented** (Pydantic + JSON Schema)
- Storage adapter: **implemented** (`GraphStore` + `LocalGraphStore`)
- Fixture integration test: **implemented**
- CI baseline: **implemented**
- Contribution/versioning policy: **implemented**
- Full MCP implementation: **deferred to Stage 4**
