"""SDD traceability records for the Stage 2 commit pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Iterable

from .models import SpecClause
from ..versioning import GraphCommit


@dataclass(frozen=True)
class TraceLink:
    link_id: str
    relation: str
    source: str
    target: str
    commit_id: str
    spec_ref: str
    metadata: dict[str, object]


class TraceabilityStore:
    """Append-only traceability ledger linking SDD clauses to evidence and commits."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "trace.jsonl"

    def append(self, links: Iterable[TraceLink]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            for link in links:
                handle.write(json.dumps(asdict(link), sort_keys=True) + "\n")

    def links(self) -> list[TraceLink]:
        if not self.path.exists():
            return []
        return [TraceLink(**json.loads(line)) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def for_spec(self, spec_ref: str) -> list[TraceLink]:
        return [link for link in self.links() if link.spec_ref == spec_ref]

    def for_commit(self, commit_id: str) -> list[TraceLink]:
        return [link for link in self.links() if link.commit_id == commit_id]


def build_trace_links(
    commit: GraphCommit,
    clauses: Iterable[SpecClause],
    *,
    test_refs: Iterable[str] = (),
) -> list[TraceLink]:
    """Create the canonical Spec -> Test -> Implementation -> Commit links."""
    clauses_by_id = {clause.id: clause for clause in clauses}
    links: list[TraceLink] = []
    tests = sorted(set(test_refs) | {clauses_by_id[r].test_ref for r in commit.spec_refs if r in clauses_by_id and clauses_by_id[r].test_ref})

    for spec_ref in commit.spec_refs:
        clause = clauses_by_id.get(spec_ref)
        if clause is None:
            continue
        spec_id = f"spec:{clause.id}"
        commit_node = f"commit:{commit.commit_id}"
        links.append(TraceLink(f"{commit.commit_id}:{clause.id}:commit", "IMPLEMENTED_BY", spec_id, commit_node, commit.commit_id, clause.id, {"tier": clause.tier.value}))
        for test_ref in tests:
            if test_ref == clause.test_ref:
                links.append(TraceLink(f"{commit.commit_id}:{clause.id}:test", "PROVEN_BY", spec_id, f"test:{test_ref}", commit.commit_id, clause.id, {"test_ref": test_ref}))

        affected = _affected_ids(commit.delta)
        for node_id in affected:
            links.append(TraceLink(f"{commit.commit_id}:{clause.id}:{node_id}", "AFFECTS", commit_node, node_id, commit.commit_id, clause.id, {}))

    return links


def _affected_ids(delta: dict[str, object]) -> list[str]:
    result: set[str] = set()
    nodes = delta.get("nodes", {})
    edges = delta.get("edges", {})
    if isinstance(nodes, dict):
        for key in ("added", "removed", "modified"):
            items = nodes.get(key, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        if "id" in item:
                            result.add(str(item["id"]))
                        elif "after" in item and isinstance(item["after"], dict) and "id" in item["after"]:
                            result.add(str(item["after"]["id"]))
    if isinstance(edges, dict):
        for key in ("added", "removed", "modified"):
            items = edges.get(key, [])
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    result.update(str(item[k]) for k in ("source", "target") if k in item)
                    for side in ("before", "after"):
                        value = item.get(side)
                        if isinstance(value, dict):
                            result.update(str(value[k]) for k in ("source", "target") if k in value)
    return sorted(result)
