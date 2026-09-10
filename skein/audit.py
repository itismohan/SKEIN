"""Exportable compliance/security review artifact."""
from __future__ import annotations
from pathlib import Path
import json
from .versioning import VersionedGraphStore, diff_graphs
from .sdd.traceability import TraceabilityStore
from .compression.telemetry import CompressionTelemetry


def generate(root: Path, *, commit_id: str | None = None, from_commit: str | None = None, to_commit: str | None = None) -> str:
    history = root / ".skein" / "history"
    store = VersionedGraphStore(history)
    target = commit_id or to_commit or store.head
    trace = TraceabilityStore(history)
    links = trace.for_commit(target) if target else trace.links()
    structural = {}
    if from_commit and target:
        structural = diff_graphs(store.state_at(from_commit), store.state_at(target))
    elif target:
        commit = store.get_commit(target)
        structural = commit.delta if commit else {}
    compression = CompressionTelemetry(history).records()
    if target:
        compression = [r for r in compression if r.get("metadata", {}).get("commit_id") in (None, target)]
    return "# Skein Audit Report\n\n" + \
        f"- Target commit: `{target or 'HEAD'}`\n- Generated from append-only graph history, traceability and compression verification logs.\n\n" + \
        "## Traceability\n\n" + ("\n".join(f"- **{l.relation}** `{l.source}` → `{l.target}` (spec `{l.spec_ref}`)" for l in links) or "- No traceability links recorded.") + "\n\n" + \
        "## Structural Diff\n\n```json\n" + json.dumps(structural, indent=2, sort_keys=True) + "\n```\n\n" + \
        "## Compression Verification\n\n```json\n" + json.dumps(compression, indent=2, sort_keys=True) + "\n```\n"
