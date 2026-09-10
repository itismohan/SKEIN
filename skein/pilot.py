"""Design-partner pilot harness for measuring Skein against a raw-context baseline.

The pilot intentionally measures deterministic, locally reproducible signals. It does not
claim LLM quality or production savings unless an external runner supplies those metrics.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .benchmarks import CASES, graph_context, raw_context, tokens
from . import __version__
from .compression.eval import run_eval
from .mcp.benchmark import measure_duplicate_context
from .store import LocalGraphStore
from .versioning import VersionedGraphStore

CONFIG_NAME = ".skein/pilot.json"
RESULT_NAME = ".skein/pilot-results.json"
REPORT_NAME = ".skein/pilot-report.md"
SCENARIO_RESULT_NAME = ".skein/pilot-scenario-results.json"
SCENARIO_REPORT_NAME = ".skein/pilot-scenario-report.md"


@dataclass(frozen=True)
class PilotConfig:
    name: str = "skein-design-partner-pilot"
    agents: int = 3
    benchmark_cases: tuple[str, ...] = tuple(c.id for c in CASES)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"benchmark_cases": list(self.benchmark_cases)}


@dataclass(frozen=True)
class CaseResult:
    id: str
    question: str
    baseline_tokens: int
    skein_tokens: int
    token_reduction_pct: float
    expected_callers: list[str]
    retrieved_callers: list[str]
    precision: float
    recall: float
    f1: float
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _precision_recall(expected: set[str], actual: set[str]) -> tuple[float, float, float]:
    tp = len(expected & actual)
    precision = tp / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return precision, recall, f1


def _retrieved_callers(store: LocalGraphStore, question: str) -> list[str]:
    target = re.search(r"calls ([\w.:-]+)", question, re.I)
    if not target:
        return []
    needle = target.group(1).strip("'\"")
    matches = [
        n for n, d in store.graph.nodes(data=True)
        if needle in n
        or needle == d.get("attributes", {}).get("name")
        or needle == d.get("attributes", {}).get("qualified_name")
    ]
    callers: set[str] = set()
    for target_node in matches:
        for caller, _, edge_data in store.graph.in_edges(target_node, data=True):
            if edge_data.get("type") == "CALLS":
                callers.add(caller.rsplit(":", 1)[-1])
    return sorted(callers)


def _context_file_count(root: Path) -> int:
    return sum(
        1
        for p in root.rglob("*")
        if p.is_file() and ".skein" not in p.parts and p.suffix.lower() in {".py", ".js", ".ts", ".md", ".txt", ".rst"}
    )


def init_pilot(root: Path, *, name: str = "skein-design-partner-pilot", agents: int = 3) -> Path:
    path = root / CONFIG_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    config = PilotConfig(name=name, agents=agents)
    path.write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def load_config(root: Path) -> PilotConfig:
    path = root / CONFIG_NAME
    if not path.exists():
        return PilotConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    valid_ids = {c.id for c in CASES}
    selected = tuple(x for x in data.get("benchmark_cases", []) if x in valid_ids)
    return PilotConfig(
        name=str(data.get("name", "skein-design-partner-pilot")),
        agents=max(1, int(data.get("agents", 3))),
        benchmark_cases=selected or tuple(c.id for c in CASES),
    )


def run_pilot(root: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_config(root)
    graph_path = root / ".skein" / "graph.json"
    if not graph_path.exists():
        raise FileNotFoundError(".skein/graph.json does not exist; run skein init/ingest first")

    store = LocalGraphStore.load(graph_path)
    case_map = {c.id: c for c in CASES}
    cases: list[CaseResult] = []
    for case_id in config.benchmark_cases:
        case = case_map[case_id]
        started = time.perf_counter()
        raw = raw_context(root, case.question)
        raw_tokens = tokens(raw)
        skein = graph_context(store, case.question)
        skein_tokens = tokens(skein)
        actual = _retrieved_callers(store, case.question)
        precision, recall, f1 = _precision_recall(set(case.expected_callers), set(actual))
        elapsed = (time.perf_counter() - started) * 1000
        reduction = (1 - skein_tokens / raw_tokens) * 100 if raw_tokens else 0.0
        cases.append(CaseResult(
            id=case.id,
            question=case.question,
            baseline_tokens=raw_tokens,
            skein_tokens=skein_tokens,
            token_reduction_pct=round(reduction, 2),
            expected_callers=list(case.expected_callers),
            retrieved_callers=actual,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            latency_ms=round(elapsed, 2),
        ))

    total_raw = sum(c.baseline_tokens for c in cases)
    total_skein = sum(c.skein_tokens for c in cases)
    total_expected = sum(len(c.expected_callers) for c in cases)
    total_retrieved = sum(len(c.retrieved_callers) for c in cases)
    total_tp = sum(len(set(c.expected_callers) & set(c.retrieved_callers)) for c in cases)
    precision = total_tp / total_retrieved if total_retrieved else 0.0
    recall = total_tp / total_expected if total_expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    history = root / ".skein" / "history"
    versioned = VersionedGraphStore(history)
    trace_path = history / "trace.jsonl"
    trace_links = 0
    if trace_path.exists():
        trace_links = sum(1 for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip())
    traceability = 1.0 if trace_links else 0.0

    compression_path = root / "eval" / "compression_eval.json"
    compression = run_eval(compression_path) if compression_path.exists() else {
        "cases": 0, "missed_items": 0, "passed": None
    }
    duplicate = measure_duplicate_context(config.agents)

    result: dict[str, Any] = {
        "pilot": config.name,
        "version": __version__,
        "generated_at_epoch": time.time(),
        "workspace": str(root),
        "graph": {
            "nodes": store.graph.number_of_nodes(),
            "edges": store.graph.number_of_edges(),
            "head": versioned.head,
            "source_files": _context_file_count(root),
        },
        "context_efficiency": {
            "baseline_tokens": total_raw,
            "skein_tokens": total_skein,
            "token_reduction_pct": round((1 - total_skein / total_raw) * 100, 2) if total_raw else 0.0,
            "duplicate_context_reduction_pct": duplicate["reduction_pct"],
        },
        "retrieval": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "cases": len(cases),
        },
        "traceability": {
            "recorded_links": trace_links,
            "coverage_signal": traceability,
        },
        "compression": {
            "cases": compression.get("cases", 0),
            "missed_items": compression.get("missed_items", 0),
            "passed": compression.get("passed"),
            "available": compression_path.exists(),
        },
        "governance": {
            "identity_scoped_mcp": True,
            "write_proposals_require_commit_authorization": True,
            "sandbox_default_subprocess": "DENY",
            "sandbox_default_network": "DENY",
        },
        "cases": [c.to_dict() for c in cases],
        "limitations": [
            "Token counts use whitespace tokens, not provider tokenizer counts.",
            "Retrieval cases are deterministic structural queries, not LLM answer-quality evaluation.",
            "No production LLM latency, cost, or developer-velocity claim is inferred from this local run.",
            "Design-partner adoption and registry publication remain external validation gates.",
        ],
    }
    return result


def write_pilot_result(root: Path, result: dict[str, Any]) -> Path:
    path = root / RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render_report(result: dict[str, Any]) -> str:
    e = result["context_efficiency"]
    r = result["retrieval"]
    g = result["graph"]
    lines = [
        "# Skein Pilot Report",
        "",
        f"**Pilot:** {result['pilot']}  ",
        f"**Software:** {result['version']}  ",
        f"**Graph:** {g['nodes']} nodes / {g['edges']} edges  ",
        f"**History head:** `{g['head'] or 'none'}`",
        "",
        "## Executive scorecard",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Context token reduction | {e['token_reduction_pct']:.2f}% |",
        f"| Duplicate-context reduction | {e['duplicate_context_reduction_pct']:.2f}% |",
        f"| Retrieval precision | {r['precision']:.2%} |",
        f"| Retrieval recall | {r['recall']:.2%} |",
        f"| Retrieval F1 | {r['f1']:.2%} |",
        f"| Compression evaluation | {('PASS' if result['compression']['passed'] else 'FAIL') if result['compression']['available'] else 'NOT RUN'} ({result['compression']['cases']} cases) |",
        f"| Traceability records | {result['traceability']['recorded_links']} |",
        "",
        "## Case results",
        "",
        "| Case | Raw | Skein | Reduction | P | R | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for c in result["cases"]:
        lines.append(
            f"| {c['id']} | {c['baseline_tokens']} | {c['skein_tokens']} | {c['token_reduction_pct']:.2f}% | "
            f"{c['precision']:.2%} | {c['recall']:.2%} | {c['f1']:.2%} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "The local pilot establishes a reproducible baseline for the structural context thesis: Skein retrieves a targeted subgraph rather than reconstructing repository context from raw files. The result is a measurement artifact, not a claim of production LLM savings or autonomous-agent quality.",
        "",
        "## Next design-partner measurements",
        "",
        "1. Capture provider-token counts and actual model spend for matched workflows.",
        "2. Compare agent task completion, rework, latency, and handoff loss with and without Skein.",
        "3. Measure traceability coverage from requirement/ticket through graph change and review.",
        "4. Record blocked unsafe writes and governance exceptions.",
        "5. Run the same scenarios for at least two external agent clients/frameworks before making interoperability claims.",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in result["limitations"])
    return "\n".join(lines) + "\n"


def write_pilot_report(root: Path, result: dict[str, Any]) -> Path:
    path = root / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(result), encoding="utf-8")
    return path


@dataclass(frozen=True)
class ScenarioCommand:
    name: str
    baseline: tuple[str, ...]
    skein: tuple[str, ...]


def init_scenario_pilot(root: Path, *, name: str = "skein-design-partner-pilot") -> Path:
    """Create a safe argv-based pilot scenario template for a real repository.

    Commands are executed without a shell. The template intentionally contains placeholders
    so a design partner must explicitly choose the workflow commands to compare.
    """
    path = root / ".skein" / "pilot-scenarios.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pilot": name,
        "timeout_seconds": 900,
        "scenarios": [
            {
                "id": "S01",
                "name": "targeted-engineering-task",
                "baseline": ["python", "-c", "print('REPLACE_WITH_BASELINE_WORKFLOW')"],
                "skein": ["python", "-c", "print('REPLACE_WITH_SKEIN_WORKFLOW')"],
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _git_snapshot(root: Path) -> str | None:
    import subprocess
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True,
            text=True, timeout=10, check=False
        )
        return proc.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def run_scenario_pilot(root: Path) -> dict[str, Any]:
    """Execute configured baseline/Skein workflows and capture objective pilot signals."""
    import subprocess
    config_path = root / ".skein" / "pilot-scenarios.json"
    if not config_path.exists():
        raise FileNotFoundError(".skein/pilot-scenarios.json does not exist; run pilot-scenario-init first")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    timeout = max(1, int(config.get("timeout_seconds", 900)))
    results: list[dict[str, Any]] = []
    for scenario in config.get("scenarios", []):
        sid = str(scenario.get("id", "scenario"))
        name = str(scenario.get("name", sid))
        for mode in ("baseline", "skein"):
            argv = scenario.get(mode)
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                raise ValueError(f"Scenario {sid} {mode} must be a non-empty argv list")
            before = _git_snapshot(root)
            started = time.perf_counter()
            try:
                proc = subprocess.run(
                    argv, cwd=root, capture_output=True, text=True, timeout=timeout,
                    check=False, shell=False,
                )
                timed_out = False
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
                exit_code = proc.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
                stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
                exit_code = None
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            after = _git_snapshot(root)
            results.append({
                "scenario_id": sid,
                "scenario": name,
                "mode": mode,
                "argv": argv,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "latency_ms": elapsed_ms,
                "stdout_tokens": tokens(stdout),
                "stderr_tokens": tokens(stderr),
                "git_status_changed": before != after,
            })
    return {
        "pilot": str(config.get("pilot", "skein-design-partner-pilot")),
        "generated_at_epoch": time.time(),
        "workspace": str(root.resolve()),
        "timeout_seconds": timeout,
        "results": results,
        "limitations": [
            "Workflow outcome quality must be reviewed by the pilot owner; process exit is not task success.",
            "Captured stdout/stderr tokens are proxies unless provider/model telemetry is supplied.",
            "Commands are executed without a shell, but pilot owners remain responsible for command safety.",
        ],
    }


def render_scenario_report(result: dict[str, Any]) -> str:
    rows = result.get("results", [])
    lines = [
        "# Skein Design-Partner Scenario Report", "",
        f"**Pilot:** {result['pilot']}  ",
        f"**Workspace:** `{result['workspace']}`", "",
        "| Scenario | Mode | Exit | Latency (ms) | Out tokens | Err tokens | Git changed |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['scenario_id']} — {row['scenario']} | {row['mode']} | "
            f"{row['exit_code'] if row['exit_code'] is not None else 'TIMEOUT'} | "
            f"{row['latency_ms']:.2f} | {row['stdout_tokens']} | {row['stderr_tokens']} | "
            f"{'yes' if row['git_status_changed'] else 'no'} |"
        )
    lines += ["", "## Interpretation", "", "Do not treat process success, token proxies, or latency alone as evidence of engineering quality improvement.", ""]
    lines += ["## Limitations", ""] + [f"- {x}" for x in result.get("limitations", [])]
    return "\n".join(lines) + "\n"


def write_scenario_result(root: Path, result: dict[str, Any]) -> Path:
    path = root / SCENARIO_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
