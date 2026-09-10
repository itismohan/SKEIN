from pathlib import Path
from skein.schema import GraphDocument, GraphNode, NodeType
from skein.versioning import VersionedGraphStore

def test_rapid_sequential_writes(tmp_path: Path):
    store=VersionedGraphStore(tmp_path/"history")
    parent=None
    for i in range(100):
        graph=GraphDocument(nodes=[GraphNode(id=f"function:{i}", type=NodeType.FUNCTION, attributes={"name":f"f{i}"})], edges=[])
        commit=store.commit(graph, author="load-test", spec_refs=("SKN-001",), expected_parent=parent)
        parent=commit.commit_id
    assert len(list(store.commits())) == 100
    assert store.head == parent
