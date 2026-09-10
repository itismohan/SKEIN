"""SDD-governed graph mutation pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import SpecClause, SpecTier
from .validator import SpecValidationError, validate_clauses
from .traceability import TraceabilityStore, build_trace_links
from ..schema import GraphDocument
from ..versioning import GraphCommit, VersionedGraphStore
from ..sanity import check_graph


class TraceabilityError(ValueError):
    pass


class SDDCommitPipeline:
    """Require a valid SDD reference before a graph mutation can be accepted."""

    def __init__(self, store: VersionedGraphStore, spec_root: Path, trace_root: Path | None = None) -> None:
        self.store = store
        self.spec_root = spec_root
        self.trace = TraceabilityStore(trace_root or store.root)

    def commit(
        self,
        new_graph: GraphDocument,
        *,
        author: str,
        message: str,
        spec_refs: Iterable[str],
        expected_parent: str | None = None,
        test_refs: Iterable[str] = (),
    ) -> GraphCommit:
        clauses = load_and_validate(self.spec_root)
        refs = tuple(sorted(set(spec_refs)))
        if not refs:
            raise TraceabilityError("accepted graph mutations require at least one SDD spec reference")
        by_id = {c.id: c for c in clauses}
        missing = sorted(set(refs) - set(by_id))
        if missing:
            raise TraceabilityError(f"unknown SDD clause(s): {', '.join(missing)}")
        sanity = check_graph(new_graph)
        if not sanity.valid:
            raise TraceabilityError("graph sanity check failed: " + "; ".join(sanity.errors))
        for ref in refs:
            clause = by_id[ref]
            if clause.tier == SpecTier.C and clause.status == "active":
                raise TraceabilityError(f"{ref}: Tier C cannot authorize a commit")
            if clause.tier == SpecTier.A and not clause.test_ref and not test_refs:
                raise TraceabilityError(f"{ref}: Tier A commit requires executable test evidence")

        commit = self.store.commit(
            new_graph,
            author=author,
            message=message,
            spec_refs=refs,
            expected_parent=expected_parent,
        )
        links = build_trace_links(commit, clauses, test_refs=test_refs)
        self.trace.append(links)
        return commit


def load_and_validate(spec_root: Path) -> list[SpecClause]:
    from .validator import load_clauses
    clauses = load_clauses(spec_root)
    validate_clauses(clauses)
    return clauses
