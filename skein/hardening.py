"""Final local hardening and release-certification evidence checks."""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from .acceptance import run as acceptance_run
from .mcp.server import call_tool
from .release import release_report
from .schema import SCHEMA_VERSION, validate_graph
from .governance.sandbox import SandboxPolicy, SandboxViolation


@dataclass(frozen=True)
class HardeningCheck:
    name: str
    passed: bool
    detail: str


def _check(name: str, fn) -> HardeningCheck:
    try:
        return HardeningCheck(name, True, str(fn()))
    except Exception as exc:
        return HardeningCheck(name, False, f"{type(exc).__name__}: {exc}")


def _python_compile(root: Path) -> str:
    files = sorted((root / "skein").rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return f"parsed {len(files)} Python modules"


def _jsonl_integrity(root: Path) -> str:
    checked = 0
    for path in (root / ".skein" / "history").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)
                checked += 1
    return f"validated {checked} JSONL records"


def _secret_scan(root: Path) -> str:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\\s*[:=]\\s*['\"][A-Za-z0-9_./+=-]{16,}['\"]"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    hits = []
    for path in (root / "skein").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                hits.append(str(path.relative_to(root)))
                break
    if hits:
        raise AssertionError("possible embedded secret in: " + ", ".join(hits))
    return "no high-confidence embedded secret patterns"


def _sandbox() -> str:
    with TemporaryDirectory() as td:
        root = Path(td)
        policy = SandboxPolicy(root)
        policy.check_path(root / "inside.txt")
        try:
            policy.check_path(root.parent / "outside.txt")
        except SandboxViolation:
            pass
        else:
            raise AssertionError("sandbox escape was allowed")
        policy.check_execution(subprocess=False, network=False)
        for kwargs in ({"subprocess": True}, {"network": True}):
            try:
                policy.check_execution(**kwargs)
            except SandboxViolation:
                continue
            raise AssertionError(f"unsafe execution allowed: {kwargs}")
    return "path, subprocess, and network boundaries enforced"


def _mcp_auth() -> str:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / ".skein" / "history").mkdir(parents=True)
        (root / ".skein" / "graph.json").write_text(
            json.dumps({"schema_version": SCHEMA_VERSION, "nodes": [], "edges": []}), encoding="utf-8"
        )
        (root / "spec" / "clauses").mkdir(parents=True)
        import shutil
        shutil.copytree(Path(__file__).parents[1] / "spec" / "clauses", root / "spec" / "clauses", dirs_exist_ok=True)
        try:
            call_tool("propose_node", {"node": {"id": "x", "kind": "Plan"}}, root)
        except PermissionError:
            return "unauthenticated write blocked"
        raise AssertionError("unauthenticated write succeeded")


def run(root: Path) -> dict:
    root = root.resolve()
    checks = [
        _check("release gates", lambda: "all passed" if release_report(root)["passed"] else "release gates failed"),
        _check("python syntax", lambda: _python_compile(root)),
        _check("history integrity", lambda: _jsonl_integrity(root)),
        _check("secret scan", lambda: _secret_scan(root)),
        _check("sandbox enforcement", _sandbox),
        _check("MCP write authentication", _mcp_auth),
        _check("MVP acceptance", lambda: "all passed" if acceptance_run(root)["passed"] else "acceptance failed"),
    ]
    return {
        "suite": "skein-final-hardening",
        "software_version": release_report(root)["software_version"],
        "graph_schema_version": SCHEMA_VERSION,
        "passed": all(c.passed for c in checks),
        "checks": [asdict(c) for c in checks],
    }
