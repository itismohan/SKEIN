from pathlib import Path
import pytest
from skein.schema import GraphDocument, GraphNode, NodeType
from skein.versioning import VersionedGraphStore, ConcurrentWriteError


def g(name):
    return GraphDocument(nodes=[GraphNode(id=name, type=NodeType.FUNCTION, attributes={"name": name})], edges=[])


def test_stale_write_persists_conflict(tmp_path: Path):
    store = VersionedGraphStore(tmp_path / "history")
    first = store.commit(g("a"), author="writer-a", spec_refs=("SKN-001",), expected_parent=None)
    with pytest.raises(ConcurrentWriteError):
        store.commit(g("b"), author="writer-b", spec_refs=("SKN-001",), expected_parent=None)
    conflicts = store.conflicts()
    assert len(conflicts) == 1
    assert conflicts[0]["expected_parent"] is None
    assert conflicts[0]["actual_head"] == first.commit_id
