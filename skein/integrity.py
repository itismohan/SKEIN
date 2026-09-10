"""Integrity verification for Skein's append-only graph history."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import GraphDocument, validate_graph
from .versioning import VersionedGraphStore


@dataclass(frozen=True)
class IntegrityResult:
    passed: bool
    commits: int
    head: str | None
    errors: tuple[str, ...]


def _expected_commit_id(record: dict[str, Any]) -> str:
    material = json.dumps(
        {
            "parent": record.get("parent_version"),
            "timestamp": record.get("timestamp"),
            "author": record.get("author"),
            "message": record.get("message"),
            "spec_refs": sorted(record.get("spec_refs", [])),
            "delta": record.get("delta", {}),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def verify_history(root: Path) -> IntegrityResult:
    """Verify commit IDs, parent continuity, delta replay, and materialized head."""
    root = root.resolve()
    history = root / ".skein" / "history"
    log_path = history / "commits.jsonl"
    errors: list[str] = []
    records: list[dict[str, Any]] = []

    if log_path.exists():
        for lineno, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append(f"commits.jsonl:{lineno}: invalid JSON: {exc}")

    previous: str | None = None
    replay = GraphDocument(nodes=[], edges=[])
    store = VersionedGraphStore(history)
    for index, record in enumerate(records, 1):
        cid = record.get("commit_id")
        if cid != _expected_commit_id(record):
            errors.append(f"commit {index}: commit_id mismatch ({cid!r})")
        if record.get("parent_version") != previous:
            errors.append(
                f"commit {cid or index}: parent mismatch; expected {previous!r}, got {record.get('parent_version')!r}"
            )
        try:
            store._apply_delta_to(replay, record["delta"])
        except Exception as exc:
            errors.append(f"commit {cid or index}: delta replay failed: {exc}")
        previous = cid

    state_path = history / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state_graph = GraphDocument.model_validate(state.get("graph", {}))
            validate_graph(state_graph)
            if state.get("head") != previous:
                errors.append(f"state head mismatch; log={previous!r}, state={state.get('head')!r}")
            def canonical(graph: GraphDocument) -> dict[str, Any]:
                payload = graph.to_contract()
                payload["nodes"] = sorted(payload["nodes"], key=lambda x: x["id"])
                payload["edges"] = sorted(payload["edges"], key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
                return payload
            if canonical(state_graph) != canonical(replay):
                errors.append("materialized state does not match replayed history")
        except Exception as exc:
            errors.append(f"state.json validation failed: {exc}")

    return IntegrityResult(not errors, len(records), previous, tuple(errors))
