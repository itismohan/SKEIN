"""Offline interoperability and MVP certification evidence."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
from .frameworks.framework_a import run_pipeline as run_a
from .frameworks.framework_b import run_pipeline as run_b
from .benchmark import measure_duplicate_context
from ..acceptance import run as acceptance_run


def _workspace(root: Path) -> Path:
    ws = root / ".skein"
    (ws / "history").mkdir(parents=True, exist_ok=True)
    (ws / "graph.json").write_text(json.dumps({"schema_version":"1.0.0","nodes":[],"edges":[]}), encoding="utf-8")
    (root / "spec" / "clauses").mkdir(parents=True, exist_ok=True)
    src = Path(__file__).parents[2] / "spec" / "clauses"
    shutil.copytree(src, root / "spec" / "clauses", dirs_exist_ok=True)
    return ws


def run_certification(source_root: Path) -> dict:
    with TemporaryDirectory() as td:
        root = Path(td)
        _workspace(root)
        a = run_a(root)
        b = run_b(root)
        acceptance = acceptance_run(source_root)
        context = measure_duplicate_context(3)
        checks = {
            "framework_a_pipeline": bool(a.commit_id),
            "framework_b_pipeline": bool(b.commit_id),
            "shared_context_reduction": context["reduction_pct"] > 0,
            "mvp_acceptance": acceptance["passed"],
        }
        return {
            "suite": "skein-mvp-certification",
            "passed": all(checks.values()),
            "checks": checks,
            "frameworks": {
                "framework-a": {"calls": a.calls, "commit_id": a.commit_id},
                "framework-b": {"calls": b.calls, "commit_id": b.commit_id},
            },
            "shared_context": context,
            "acceptance": acceptance,
        }
