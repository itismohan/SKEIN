"""Local health checks for the Skein graph store and append-only logs."""
from __future__ import annotations
from pathlib import Path
import json
from .schema import GraphDocument, validate_graph
from .versioning import VersionedGraphStore


def check(root: Path) -> dict:
    root = root.resolve(); skein = root / '.skein'; history = skein / 'history'
    checks: list[dict[str, object]] = []
    graph_path = skein / 'graph.json'
    if not graph_path.exists():
        checks.append({'name':'graph_store','passed':False,'detail':'graph.json missing'})
    else:
        try:
            doc = GraphDocument.model_validate(json.loads(graph_path.read_text(encoding='utf-8')))
            validate_graph(doc)
            checks.append({'name':'graph_store','passed':True,'detail':f'{len(doc.nodes)} nodes, {len(doc.edges)} edges'})
        except Exception as exc:
            checks.append({'name':'graph_store','passed':False,'detail':str(exc)})
    try:
        store = VersionedGraphStore(history)
        checks.append({'name':'version_history','passed':True,'detail':f'head={store.head}, commits={len(store.commits())}'})
        conflicts = len(store.conflicts())
        checks.append({'name':'conflicts','passed':conflicts == 0,'detail':f'{conflicts} persisted conflicts'})
    except Exception as exc:
        checks.append({'name':'version_history','passed':False,'detail':str(exc)})
    return {'service':'skein','status':'ok' if all(bool(c['passed']) for c in checks) else 'degraded','checks':checks}
