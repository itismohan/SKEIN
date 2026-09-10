from pathlib import Path
import json
import pytest
from skein.schema import GraphDocument, GraphNode, GraphEdge, NodeType, EdgeType
from skein.versioning import VersionedGraphStore, ConcurrentWriteError, diff_graphs


def graph(confidence="EXTRACTED"):
    a = GraphNode(id="function:a", type=NodeType.FUNCTION, attributes={"name": "a"})
    b = GraphNode(id="function:b", type=NodeType.FUNCTION, attributes={"name": "b"})
    e = GraphEdge(source=a.id, target=b.id, type=EdgeType.CALLS, attributes={"confidence": confidence})
    return GraphDocument(nodes=[a, b], edges=[e])


def test_diff_reports_confidence_change():
    d = diff_graphs(graph(), graph("INFERRED"))
    assert d["confidence_changes"][0]["before"] == "EXTRACTED"
    assert d["confidence_changes"][0]["after"] == "INFERRED"


def test_commit_is_append_only_and_has_parent(tmp_path: Path):
    store = VersionedGraphStore(tmp_path / ".skein" / "history")
    first = store.commit(graph(), author="tester", message="initial", spec_refs=["SKN-001"])
    second_graph = graph("INFERRED")
    second = store.commit(second_graph, author="tester", message="confidence update", spec_refs=["SKN-002"], expected_parent=first.commit_id)
    assert second.parent_version == first.commit_id
    lines = (tmp_path / ".skein" / "history" / "commits.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert store.head == second.commit_id
    assert store.graph == second_graph
    assert json.loads(lines[0])["commit_id"] == first.commit_id


def test_stale_write_rejected(tmp_path: Path):
    store = VersionedGraphStore(tmp_path / "history")
    first = store.commit(graph(), spec_refs=["SKN-001"])
    store.commit(graph("INFERRED"), expected_parent=first.commit_id, spec_refs=["SKN-002"])
    with pytest.raises(ConcurrentWriteError):
        store.commit(graph(), expected_parent=first.commit_id, spec_refs=["SKN-003"])
