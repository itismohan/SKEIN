"""Stage 6 release gates and migration helpers."""
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

from . import __version__
from .schema import SCHEMA_VERSION, validate_graph
from .sdd import load_clauses, validate_clauses


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    detail: str


def run_release_gates(root: Path) -> list[Gate]:
    root = root.resolve()
    gates: list[Gate] = []
    required = [
        "README.md", "CONTRIBUTING.md", "docs/schema-reference.md",
        "docs/mcp-reference.md", "docs/migration-guide.md",
        "docs/deprecation-policy.md", "docs/stage-6-release.md", "docs/stage-6-hardening.md", "docs/production-runbook.md", "docs/v0.3-pilot-intelligence.md", "docs/v0.5-evaluation.md", "docs/v0.5-release.md", "docs/v0.6-experimental-control-plane.md", "docs/v0.6-release.md", "docs/v0.7-agent-execution.md", "docs/v0.7-agent-adapters.md", "docs/v0.7-provider-execution-bridges.md", "docs/v0.7-release.md", "docs/v0.8-adaptive-context-intelligence.md", "docs/v0.8-release.md", "docs/v0.9-autonomous-quality-loop.md", "docs/v0.9-release.md", "docs/v1.0-ai-dlc-control-plane.md", "docs/v1.0-release.md", "schemas/control-plane.schema.json", "skill/skein/SKILL.md", "packages/mcp-protocol/schemas/mcp-tools.json",
    ]
    missing = [p for p in required if not (root / p).exists()]
    gates.append(Gate("release documentation", not missing, "missing: " + ", ".join(missing) if missing else "complete"))

    try:
        clauses = load_clauses(root / "spec" / "clauses")
        validate_clauses(clauses)
        gates.append(Gate("SDD contract", True, f"{len(clauses)} clauses valid"))
    except Exception as exc:
        gates.append(Gate("SDD contract", False, str(exc)))

    schema_path = root / "schemas" / "graph.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        gates.append(Gate("graph schema", schema.get("$id", "").endswith(SCHEMA_VERSION), f"version={SCHEMA_VERSION}"))
    except Exception as exc:
        gates.append(Gate("graph schema", False, str(exc)))

    tmp = list(root.rglob("*.tmp"))
    gates.append(Gate("repository hygiene", not tmp, "temporary files: " + ", ".join(str(x.relative_to(root)) for x in tmp) if tmp else "clean"))
    gates.append(Gate("version declarations", bool(__version__) and bool(SCHEMA_VERSION), f"software={__version__}, schema={SCHEMA_VERSION}"))
    return gates


def release_report(root: Path) -> dict:
    gates = run_release_gates(root)
    return {
        "software_version": __version__,
        "graph_schema_version": SCHEMA_VERSION,
        "passed": all(g.passed for g in gates),
        "gates": [g.__dict__ for g in gates],
    }


def migrate_workspace(root: Path) -> dict:
    """Migrate a pre-0.1 workspace into the versioned history layout."""
    from .store import LocalGraphStore
    from .versioning import VersionedGraphStore

    root = root.resolve()
    skein = root / ".skein"
    graph_path = skein / "graph.json"
    history = skein / "history"
    if not graph_path.exists():
        return {"migrated": False, "reason": "no graph.json"}
    store = VersionedGraphStore(history)
    if store.head:
        return {"migrated": False, "reason": "versioned history already exists", "head": store.head}
    graph = LocalGraphStore.load(graph_path).to_document()
    commit = store.commit(graph, author="migration", message="migrate legacy Skein workspace", spec_refs=("SKN-001",), expected_parent=None)
    graph_path.write_text(json.dumps(store.graph.to_contract(), indent=2) + "\n", encoding="utf-8")
    return {"migrated": True, "commit_id": commit.commit_id}
