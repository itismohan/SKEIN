from pathlib import Path
from skein.sdd import SDDIngestionPipeline
from skein.versioning import VersionedGraphStore

ROOT = Path(__file__).parents[2]


def test_ingestion_produces_versioned_commit_and_trace(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "spec" / "clauses").mkdir(parents=True)
    for source in (ROOT / "spec" / "clauses").glob("*.yaml"):
        (repo / "spec" / "clauses" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "app.py").write_text("def pay():\n    return True\n", encoding="utf-8")
    store = VersionedGraphStore(repo / ".skein" / "history")
    report, commit = SDDIngestionPipeline(repo, versioned=store).ingest_and_commit(author="agent:ingest")
    assert report.added_files >= 1
    assert commit is not None
    assert "SKN-004" in commit.spec_refs
    assert store.head == commit.commit_id
    assert store.get_commit(commit.commit_id) is not None


def test_unchanged_ingestion_does_not_create_empty_commit(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "spec" / "clauses").mkdir(parents=True)
    for source in (ROOT / "spec" / "clauses").glob("*.yaml"):
        (repo / "spec" / "clauses" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "app.py").write_text("def pay():\n    return True\n", encoding="utf-8")
    store = VersionedGraphStore(repo / ".skein" / "history")
    _, first = SDDIngestionPipeline(repo, versioned=store).ingest_and_commit()
    _, second = SDDIngestionPipeline(repo, versioned=store).ingest_and_commit()
    assert first is not None
    assert second is None
    assert len(list(store.commits())) == 1
