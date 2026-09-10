"""Deterministic offline acceptance suite for the Skein MVP release candidate."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from .release import release_report
from .schema import GraphDocument
from .store import LocalGraphStore
from .versioning import VersionedGraphStore, diff_graphs
from .sdd import SDDIngestionPipeline, TraceabilityStore
from .compression.core import compress
from .compression.eval import run_eval
from .mcp.server import call_tool
from .mcp.benchmark import measure_duplicate_context
from .governance.sandbox import SandboxPolicy, SandboxViolation

@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str

def _check(name: str, fn) -> Check:
    try:
        detail = str(fn())
        return Check(name, True, detail)
    except Exception as exc:
        return Check(name, False, f"{type(exc).__name__}: {exc}")

def run(root: Path) -> dict:
    root = root.resolve()
    checks: list[Check] = []
    checks.append(_check("release gates", lambda: "all passed" if release_report(root)["passed"] else "release gates failed"))

    def ingest():
        with TemporaryDirectory() as td:
            ws = Path(td)
            (ws / "app.py").write_text("def main():\n    return helper()\n\ndef helper():\n    return 42\n", encoding="utf-8")
            (ws / "spec").mkdir(); (ws / "spec" / "clauses").mkdir(parents=True)
            import shutil
            shutil.copytree(root / "spec" / "clauses", ws / "spec" / "clauses", dirs_exist_ok=True)
            store = VersionedGraphStore(ws / ".skein" / "history")
            result, commit = SDDIngestionPipeline(ws, versioned=store).ingest_and_commit(author="acceptance", message="acceptance ingestion", full_rebuild=True)
            assert commit is not None
            assert result.nodes > 0 and result.edges > 0
            return f"{result.nodes} nodes, {result.edges} edges, commit={commit.commit_id}"
    checks.append(_check("versioned ingestion", ingest))

    def compression():
        text = """The operation failed with HTTP 500.\n```python\nraise RuntimeError('boom')\n```\nDo not expose API keys or credentials.\n"""
        r = compress(text, aggressiveness="balanced")
        assert r.outcome == 'pass' and "RuntimeError('boom')" in r.compressed and "HTTP 500" in r.compressed
        savings = (1 - r.compressed_tokens / r.original_tokens) * 100 if r.original_tokens else 0
        return f"outcome={r.outcome}, savings={savings:.1f}%"
    checks.append(_check("verified compression", compression))

    checks.append(_check("compression evaluation", lambda: f"{run_eval(root / 'eval' / 'compression_eval.json')['cases']} cases, missed_items={run_eval(root / 'eval' / 'compression_eval.json')['missed_items']}"))

    def mcp_flow():
        with TemporaryDirectory() as td:
            ws = Path(td); (ws / ".skein" / "history").mkdir(parents=True)
            (ws / ".skein" / "graph.json").write_text(json.dumps({"schema_version":"1.0.0","nodes":[],"edges":[]}), encoding="utf-8")
            (ws / "spec").mkdir(); (ws / "spec" / "clauses").mkdir(parents=True)
            import shutil; shutil.copytree(root / "spec" / "clauses", ws / "spec" / "clauses", dirs_exist_ok=True)
            proposed = call_tool("propose_node", {"identity":"local-admin","node":{"id":"acceptance-plan","kind":"Plan","attributes":{"title":"acceptance"}}}, ws)
            committed = call_tool("commit_proposal", {"identity":"local-admin","proposal_id":proposed["proposal_id"]}, ws)
            assert committed["status"] == "committed"
            return f"proposal={proposed['proposal_id']}, commit={committed['commit_id']}"
    checks.append(_check("MCP governed write", mcp_flow))

    checks.append(_check("shared context benchmark", lambda: f"reduction={measure_duplicate_context(3)['reduction_pct']:.2f}%"))

    def sandbox():
        with TemporaryDirectory() as td:
            policy = SandboxPolicy(Path(td))
            try:
                policy.check_path(Path(td).parent / "escape.txt")
            except SandboxViolation:
                return "path escape blocked"
            raise AssertionError("sandbox allowed path escape")
    checks.append(_check("sandbox boundary", sandbox))

    return {"suite": "skein-mvp-acceptance", "software_version": release_report(root)["software_version"], "passed": all(c.passed for c in checks), "checks": [asdict(c) for c in checks]}
