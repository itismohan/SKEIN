import json
from pathlib import Path

from skein.integrity import verify_history
from skein.versioning import VersionedGraphStore
from skein.schema import GraphDocument, GraphNode, NodeType


def test_history_integrity_detects_tampering(tmp_path: Path):
    history = tmp_path / ".skein" / "history"
    store = VersionedGraphStore(history)
    graph = GraphDocument(nodes=[GraphNode(id="a", type=NodeType.FILE, attributes={})], edges=[])
    store.commit(graph, author="test", message="add", spec_refs=("SKN-001",), expected_parent=None)
    assert verify_history(tmp_path).passed

    path = history / "commits.jsonl"
    record = json.loads(path.read_text().splitlines()[0])
    record["message"] = "tampered"
    path.write_text(json.dumps(record) + "\n")
    result = verify_history(tmp_path)
    assert not result.passed
    assert any("commit_id mismatch" in e for e in result.errors)
