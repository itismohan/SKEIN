"""SDD-governed ingestion-to-commit pipeline."""
from __future__ import annotations

from pathlib import Path

from .commit_pipeline import SDDCommitPipeline
from ..ingestion.pipeline import IncrementalIngester, IngestionReport
from ..store import LocalGraphStore
from ..versioning import GraphCommit, VersionedGraphStore

class SDDIngestionPipeline:
    """Ingest into a working graph, validate SDD authority, then commit atomically."""

    DEFAULT_SPEC = "SKN-004"

    def __init__(self, root: Path, *, versioned: VersionedGraphStore, spec_root: Path | None = None) -> None:
        self.root = root.resolve()
        self.versioned = versioned
        self.spec_root = spec_root or self.root / "spec" / "clauses"

    def ingest_and_commit(
        self, *, author: str = "ingest", message: str = "ingest graph update",
        spec_refs: tuple[str, ...] = (DEFAULT_SPEC,), full_rebuild: bool = False,
    ) -> tuple[IngestionReport, GraphCommit | None]:
        working = LocalGraphStore()
        for node in self.versioned.graph.nodes:
            working.add_node(node)
        for edge in self.versioned.graph.edges:
            working.add_edge(edge)
        ingester = IncrementalIngester(self.root, working)
        report = ingester.ingest(full_rebuild=full_rebuild, save_manifest=False)
        new_graph = working.to_document()
        if new_graph.model_dump(mode="json") == self.versioned.graph.model_dump(mode="json"):
            ingester._save_manifest()
            return report, None
        commit = SDDCommitPipeline(self.versioned, self.spec_root).commit(
            new_graph, author=author, message=message, spec_refs=spec_refs,
            expected_parent=self.versioned.head,
        )
        ingester._save_manifest()
        return report, commit
