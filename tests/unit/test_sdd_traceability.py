from pathlib import Path
import pytest
from skein.schema import GraphDocument, GraphNode, NodeType
from skein.versioning import VersionedGraphStore
from skein.sdd import SDDCommitPipeline, TraceabilityError, TraceabilityStore

ROOT = Path(__file__).parents[2]


def graph(name="a"):
    return GraphDocument(nodes=[GraphNode(id=f"function:{name}", type=NodeType.FUNCTION, attributes={"name": name})], edges=[])


def test_commit_pipeline_creates_spec_test_commit_trace(tmp_path: Path):
    store = VersionedGraphStore(tmp_path / "history")
    pipeline = SDDCommitPipeline(store, ROOT / "spec" / "clauses", tmp_path / "trace")
    commit = pipeline.commit(graph(), author="agent:coder", message="implement versioned graph history", spec_refs=["SKN-001"])
    links = TraceabilityStore(tmp_path / "trace").for_commit(commit.commit_id)
    relations = {link.relation for link in links}
    assert "IMPLEMENTED_BY" in relations
    assert "PROVEN_BY" in relations
    assert "AFFECTS" in relations


def test_commit_requires_spec_reference(tmp_path: Path):
    pipeline = SDDCommitPipeline(VersionedGraphStore(tmp_path / "history"), ROOT / "spec" / "clauses")
    with pytest.raises(TraceabilityError, match="at least one SDD spec reference"):
        pipeline.commit(graph(), author="agent", message="bad", spec_refs=[])


def test_commit_rejects_unknown_spec(tmp_path: Path):
    pipeline = SDDCommitPipeline(VersionedGraphStore(tmp_path / "history"), ROOT / "spec" / "clauses")
    with pytest.raises(TraceabilityError, match="unknown SDD clause"):
        pipeline.commit(graph(), author="agent", message="bad", spec_refs=["SKN-999"])
