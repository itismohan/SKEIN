"""SDD-governed versioned graph history for Skein Stage 2."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
from typing import Any, Iterable

from .schema import GraphDocument, GraphEdge, GraphNode, validate_graph


@dataclass(frozen=True)
class GraphCommit:
    commit_id: str
    parent_version: str | None
    timestamp: str
    author: str
    message: str
    spec_refs: tuple[str, ...]
    delta: dict[str, Any]


class VersionedGraphStore:
    """Append-only commit log with materialized graph state and deterministic IDs."""

    FORMAT_VERSION = 1

    def __init__(self, root: Path, graph: GraphDocument | None = None) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "commits.jsonl"
        self.state_path = self.root / "state.json"
        self.conflict_path = self.root / "conflicts.jsonl"
        self.graph = graph or GraphDocument(nodes=[], edges=[])
        validate_graph(self.graph)
        self.head: str | None = None
        if self.state_path.exists():
            self._load_state()
        elif self.log_path.exists():
            self._rebuild_from_log()

    def _load_state(self) -> None:
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.head = data.get("head")
        self.graph = GraphDocument.model_validate(data.get("graph", {"nodes": [], "edges": []}))
        validate_graph(self.graph)

    def _rebuild_from_log(self) -> None:
        self.graph = GraphDocument(nodes=[], edges=[])
        self.head = None
        for commit in self.commits():
            self._apply_delta(commit.delta)
            self.head = commit.commit_id
        self._persist_state()

    def _persist_state(self) -> None:
        payload = {"format_version": self.FORMAT_VERSION, "head": self.head, "graph": self.graph.to_contract()}
        self.state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def commits(self) -> Iterable[GraphCommit]:
        if not self.log_path.exists():
            return []
        result: list[GraphCommit] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                result.append(GraphCommit(**data))
        return result

    def get_commit(self, commit_id: str) -> GraphCommit | None:
        return next((c for c in self.commits() if c.commit_id == commit_id), None)

    def record_conflict(self, *, expected: str | None, actual: str | None, author: str, operation: str = "commit") -> dict[str, Any]:
        record = {"expected_parent": expected, "actual_head": actual, "author": author, "operation": operation, "timestamp": datetime.now(timezone.utc).isoformat()}
        record["conflict_id"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
        with self.conflict_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def conflicts(self) -> list[dict[str, Any]]:
        if not self.conflict_path.exists():
            return []
        return [json.loads(line) for line in self.conflict_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def commit(
        self,
        new_graph: GraphDocument,
        *,
        author: str = "system",
        message: str = "graph update",
        spec_refs: Iterable[str] = (),
        expected_parent: str | None = None,
    ) -> GraphCommit:
        validate_graph(new_graph)
        if expected_parent != self.head:
            self.record_conflict(expected=expected_parent, actual=self.head, author=author)
            raise ConcurrentWriteError(expected_parent, self.head)
        delta = diff_graphs(self.graph, new_graph)
        timestamp = datetime.now(timezone.utc).isoformat()
        material = json.dumps(
            {"parent": self.head, "timestamp": timestamp, "author": author, "message": message,
             "spec_refs": sorted(spec_refs), "delta": delta},
            sort_keys=True,
            separators=(",", ":"),
        )
        commit_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
        commit = GraphCommit(
            commit_id=commit_id,
            parent_version=self.head,
            timestamp=timestamp,
            author=author,
            message=message,
            spec_refs=tuple(sorted(spec_refs)),
            delta=delta,
        )
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(commit), sort_keys=True) + "\n")
        self.graph = new_graph
        self.head = commit_id
        self._persist_state()
        return commit

    def history(self, *, since: str | None = None, since_date: str | None = None, limit: int | None = None) -> list[GraphCommit]:
        commits = list(self.commits())
        if since_date is not None:
            commits = [c for c in commits if c.timestamp >= since_date]
        if since is not None:
            seen = False
            selected = []
            for commit in commits:
                if seen:
                    selected.append(commit)
                if commit.commit_id == since:
                    seen = True
            commits = selected
        if limit is not None:
            commits = commits[-limit:]
        return commits

    def state_at(self, commit_id: str | None) -> GraphDocument:
        state = GraphDocument(nodes=[], edges=[])
        if commit_id is None:
            return state
        found = False
        for commit in self.commits():
            self._apply_delta_to(state, commit.delta)
            if commit.commit_id == commit_id:
                found = True
                break
        if not found:
            raise KeyError(f"Unknown commit: {commit_id}")
        return state

    def rollback(self, target_commit: str, *, author: str = "system", spec_refs: Iterable[str] = ("SKN-001",)) -> GraphCommit:
        target = self.get_commit(target_commit)
        if target is None:
            raise KeyError(f"Unknown commit: {target_commit}")
        state = GraphDocument(nodes=[], edges=[])
        for commit in self.commits():
            self._apply_delta_to(state, commit.delta)
            if commit.commit_id == target_commit:
                break
        return self.commit(state, author=author, message=f"rollback to {target_commit}", spec_refs=tuple(spec_refs), expected_parent=self.head)

    def _apply_delta(self, delta: dict[str, Any]) -> None:
        self._apply_delta_to(self.graph, delta)

    @staticmethod
    def _apply_delta_to(graph: GraphDocument, delta: dict[str, Any]) -> None:
        nodes = {n.id: n for n in graph.nodes}
        edges = list(graph.edges)
        for item in delta["nodes"]["removed"]:
            nodes.pop(item["id"], None)
        for item in delta["edges"]["removed"]:
            edge = GraphEdge.model_validate(item)
            for idx, existing in enumerate(edges):
                if _edge_key(existing) == _edge_key(edge):
                    edges.pop(idx)
                    break
        for item in delta["nodes"]["added"]:
            nodes[item["id"]] = GraphNode.model_validate(item)
        for item in delta["nodes"]["modified"]:
            nodes[item["id"]] = GraphNode.model_validate(item["after"])
        for item in delta["edges"]["added"]:
            edges.append(GraphEdge.model_validate(item))
        for item in delta["edges"]["modified"]:
            before = GraphEdge.model_validate(item["before"])
            after = GraphEdge.model_validate(item["after"])
            for idx, existing in enumerate(edges):
                if _edge_key(existing) == _edge_key(before):
                    edges[idx] = after
                    break
            else:
                edges.append(after)
        graph.nodes = list(nodes.values())
        graph.edges = edges
        validate_graph(graph)



class ConcurrentWriteError(RuntimeError):
    def __init__(self, expected: str | None, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"stale graph write: expected parent {expected!r}, current head is {actual!r}")


def _edge_key(edge: GraphEdge) -> tuple[str, str, str, str]:
    return (edge.source, edge.target, edge.type.value, json.dumps(edge.attributes, sort_keys=True))


def _node_map(graph: GraphDocument) -> dict[str, GraphNode]:
    return {n.id: n for n in graph.nodes}


def _edge_map(graph: GraphDocument) -> dict[tuple[str, str, str, str], GraphEdge]:
    return {_edge_key(e): e for e in graph.edges}


def diff_graphs(before: GraphDocument, after: GraphDocument) -> dict[str, Any]:
    """Return a deterministic structural delta, including confidence changes."""
    bn, an = _node_map(before), _node_map(after)
    added_nodes = [an[k].model_dump(mode="json") for k in sorted(set(an) - set(bn))]
    removed_nodes = [{"id": bn[k].id, "type": bn[k].type.value, "attributes": bn[k].attributes} for k in sorted(set(bn) - set(an))]
    modified_nodes = []
    for key in sorted(set(bn) & set(an)):
        b, a = bn[key], an[key]
        if b.model_dump() != a.model_dump():
            modified_nodes.append({"id": key, "before": b.model_dump(mode="json"), "after": a.model_dump(mode="json")})

    # Treat edges as multisets so repeated identical calls are preserved.
    before_groups: dict[tuple[str, str, str, str], list[GraphEdge]] = {}
    after_groups: dict[tuple[str, str, str, str], list[GraphEdge]] = {}
    for edge in before.edges:
        before_groups.setdefault(_edge_key(edge), []).append(edge)
    for edge in after.edges:
        after_groups.setdefault(_edge_key(edge), []).append(edge)
    added_edges: list[dict[str, Any]] = []
    removed_edges: list[dict[str, Any]] = []
    for key in sorted(set(before_groups) | set(after_groups)):
        bs, aas = before_groups.get(key, []), after_groups.get(key, [])
        if len(aas) > len(bs):
            added_edges.extend(e.model_dump(mode="json") for e in aas[len(bs):])
        elif len(bs) > len(aas):
            removed_edges.extend(e.model_dump(mode="json") for e in bs[len(aas):])
    modified_edges = []
    confidence_changes = []
    before_by_endpoint: dict[tuple[str, str, str], list[GraphEdge]] = {}
    after_by_endpoint: dict[tuple[str, str, str], list[GraphEdge]] = {}
    for edge in before.edges:
        before_by_endpoint.setdefault((edge.source, edge.target, edge.type.value), []).append(edge)
    for edge in after.edges:
        after_by_endpoint.setdefault((edge.source, edge.target, edge.type.value), []).append(edge)
    for key in sorted(set(before_by_endpoint) & set(after_by_endpoint)):
        bs, aas = before_by_endpoint[key], after_by_endpoint[key]
        if len(bs) == 1 and len(aas) == 1 and bs[0].model_dump() != aas[0].model_dump():
            b, a = bs[0], aas[0]
            modified_edges.append({"source": key[0], "target": key[1], "type": key[2], "before": b.model_dump(mode="json"), "after": a.model_dump(mode="json")})
            bc = b.attributes.get("confidence")
            ac = a.attributes.get("confidence")
            if bc != ac:
                confidence_changes.append({"source": key[0], "target": key[1], "type": key[2], "before": bc, "after": ac})

    return {
        "nodes": {"added": added_nodes, "removed": removed_nodes, "modified": modified_nodes},
        "edges": {"added": added_edges, "removed": removed_edges, "modified": modified_edges},
        "confidence_changes": confidence_changes,
    }
