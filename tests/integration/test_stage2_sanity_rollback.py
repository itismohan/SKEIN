from pathlib import Path
import pytest
from skein.schema import GraphDocument, GraphNode, GraphEdge, NodeType, EdgeType
from skein.sanity import check_graph
from skein.versioning import VersionedGraphStore

def test_sanity_detects_orphan_edge(tmp_path: Path):
    graph=GraphDocument(nodes=[GraphNode(id="a", type=NodeType.FUNCTION)], edges=[GraphEdge(source="a", target="missing", type=EdgeType.CALLS)])
    report=check_graph(graph)
    assert not report.valid
    assert any("orphan" in e for e in report.errors)

def test_rollback_restores_known_good_state(tmp_path: Path):
    store=VersionedGraphStore(tmp_path/"history")
    good=GraphDocument(nodes=[GraphNode(id="a", type=NodeType.FUNCTION)], edges=[])
    first=store.commit(good, author="test", spec_refs=("SKN-001",), expected_parent=None)
    bad=GraphDocument(nodes=[GraphNode(id="a", type=NodeType.FUNCTION), GraphNode(id="b", type=NodeType.FUNCTION)], edges=[])
    second=store.commit(bad, author="test", spec_refs=("SKN-001",), expected_parent=first.commit_id)
    rb=store.rollback(first.commit_id, author="rollback", spec_refs=("SKN-001",))
    assert rb.parent_version == second.commit_id
    assert {n.id for n in store.graph.nodes} == {"a"}
