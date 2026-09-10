"""Skein v0.6 experimental control plane.

Provides deterministic task registration, paired-arm randomization, environment/context
fingerprinting, confound checks, power guidance, and reproducible evidence manifests.
It deliberately records experiment metadata; it does not execute arbitrary agent code.
"""
from __future__ import annotations

import hashlib, json, os, platform, random, statistics, subprocess, sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.6.0"
CONFIG_NAME = ".skein/experiment.json"
RESULT_NAME = ".skein/experiment-results.json"
REPORT_NAME = ".skein/experiment-report.md"
EVENTS_NAME = ".skein/history/experiment-events.jsonl"

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    description: str
    tags: tuple[str, ...] = ()
    difficulty: str = "medium"
    eligible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "skein-v0.6-experiment"
    seed: int = 42
    allocation_ratio: float = 0.5
    paired: bool = True
    counterbalance: bool = True
    primary_metrics: tuple[str, ...] = ("context_tokens", "cost_usd", "latency_ms")
    minimum_tasks: int = 10
    confidence_level: float = 0.95
    power_target: float = 0.80
    outlier_policy: str = "report-only"
    model: str = "unspecified"
    provider: str = "unspecified"
    prompt_hash: str = "unspecified"
    graph_head: str = "unspecified"
    repository_commit: str = "unknown"

@dataclass(frozen=True)
class Assignment:
    task_id: str
    arm: str
    order: int
    cohort: str = "default"
    seed: int = 42


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repository_commit(root: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True, timeout=3).stdout.strip()
    except Exception:
        return "unknown"


def environment_fingerprint(root: Path, config: ExperimentConfig | None = None) -> dict[str, Any]:
    config = config or ExperimentConfig(repository_commit=repository_commit(root))
    payload = {
        "skein_version": _skein_version(), "python": sys.version.split()[0],
        "platform": platform.platform(), "os": os.name,
        "repository_commit": config.repository_commit,
        "model": config.model, "provider": config.provider,
        "prompt_hash": config.prompt_hash, "graph_head": config.graph_head,
    }
    payload["fingerprint"] = fingerprint(payload)
    return payload


def _skein_version() -> str:
    try:
        from . import __version__
        return __version__
    except Exception:
        return "unknown"


def load_config(root: Path) -> ExperimentConfig:
    path = root / CONFIG_NAME
    if not path.exists():
        return ExperimentConfig(repository_commit=repository_commit(root))
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ExperimentConfig(**raw)


def save_config(root: Path, config: ExperimentConfig) -> Path:
    path = root / CONFIG_NAME; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical(asdict(config)) + "\n", encoding="utf-8"); return path


def _tasks_path(root: Path) -> Path:
    return root / ".skein" / "experiment-tasks.json"


def load_tasks(root: Path) -> list[TaskSpec]:
    path = _tasks_path(root)
    if not path.exists(): return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [TaskSpec(task_id=str(r["task_id"]), description=str(r["description"]), tags=tuple(r.get("tags", [])), difficulty=str(r.get("difficulty", "medium")), eligible=bool(r.get("eligible", True)), metadata=dict(r.get("metadata", {}))) for r in rows]


def add_tasks(root: Path, tasks: list[TaskSpec]) -> dict[str, Any]:
    existing = load_tasks(root); ids = {t.task_id for t in existing}
    added = []
    for task in tasks:
        if not task.task_id or task.task_id in ids: raise ValueError(f"duplicate or empty task_id: {task.task_id!r}")
        existing.append(task); ids.add(task.task_id); added.append(task.task_id)
    path = _tasks_path(root); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(t) for t in existing], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"added": added, "total_tasks": len(existing), "path": str(path)}


def assign_tasks(root: Path, config: ExperimentConfig | None = None, cohort: str = "default") -> list[Assignment]:
    root = root.resolve(); config = config or load_config(root)
    tasks = [t for t in load_tasks(root) if t.eligible]
    if not tasks: raise ValueError("no eligible experiment tasks")
    rng = random.Random(config.seed)
    tasks = sorted(tasks, key=lambda t: t.task_id)
    rng.shuffle(tasks)
    assignments: list[Assignment] = []
    if config.paired:
        # Every task receives both arms. Counterbalancing changes execution order,
        # not treatment membership, so each task can produce a matched observation.
        order = 0
        for index, task in enumerate(tasks):
            first = "baseline" if not config.counterbalance or index % 2 == 0 else "skein"
            second = "skein" if first == "baseline" else "baseline"
            assignments.append(Assignment(task.task_id, first, order, cohort, config.seed)); order += 1
            assignments.append(Assignment(task.task_id, second, order, cohort, config.seed)); order += 1
    else:
        n_treat = round(len(tasks) * config.allocation_ratio)
        for i, task in enumerate(tasks):
            arm = "skein" if i < n_treat else "baseline"
            assignments.append(Assignment(task.task_id, arm, i, cohort, config.seed))
    assignments.sort(key=lambda a: (a.task_id, a.arm))
    return assignments


def validate_assignments(assignments: list[Assignment], tasks: list[TaskSpec]) -> list[str]:
    errors: list[str] = []
    task_ids = {t.task_id for t in tasks if t.eligible}
    rows = {(a.task_id, a.arm) for a in assignments}
    if any(a.arm not in {"baseline", "skein"} for a in assignments): errors.append("invalid experiment arm")
    if len(rows) != len(assignments): errors.append("duplicate task/arm assignment")
    assigned_ids = {a.task_id for a in assignments}
    if assigned_ids != task_ids: errors.append("assignment/task corpus mismatch")
    for task_id in sorted(task_ids):
        arms = {a.arm for a in assignments if a.task_id == task_id}
        if arms != {"baseline", "skein"}:
            errors.append(f"task {task_id} is not paired across baseline and skein")
    return errors


def confounds(root: Path, config: ExperimentConfig, assignments: list[Assignment]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    env = environment_fingerprint(root, config)
    if config.repository_commit == "unknown": issues.append({"type":"repository", "severity":"high", "detail":"repository commit is unknown"})
    if config.model == "unspecified" or config.provider == "unspecified": issues.append({"type":"model", "severity":"medium", "detail":"provider/model not specified"})
    if config.prompt_hash == "unspecified": issues.append({"type":"prompt", "severity":"medium", "detail":"prompt fingerprint not specified"})
    if config.graph_head == "unspecified": issues.append({"type":"graph", "severity":"medium", "detail":"graph head not specified"})
    if len({a.seed for a in assignments}) > 1: issues.append({"type":"randomization", "severity":"high", "detail":"assignment seeds differ"})
    issues.append({"type":"environment", "severity":"info", "detail":env["fingerprint"]})
    return issues


def normal_z(p: float) -> float:
    """Inverse standard-normal CDF using a deterministic binary search."""
    import math
    if not 0 < p < 1:
        raise ValueError("p must be between 0 and 1")
    lo, hi = -9.0, 9.0
    for _ in range(100):
        mid = (lo + hi) / 2
        cdf = 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0)))
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def power_guidance(stddev: float, effect: float, alpha: float = .05, power: float = .8) -> dict[str, Any]:
    if stddev <= 0 or effect <= 0: raise ValueError("stddev and effect must be positive")
    import math
    z_alpha = normal_z(1-alpha/2); z_power = normal_z(power)
    n = math.ceil(((z_alpha + z_power) * stddev / effect) ** 2)
    return {"design":"paired-continuous-approximation", "stddev":stddev, "minimum_detectable_effect":effect, "alpha":alpha, "target_power":power, "approx_pairs":n, "note":"Planning guidance only; use a formal power analysis for the final study design."}


def create_manifest(root: Path, assignments: list[Assignment], config: ExperimentConfig | None = None) -> dict[str, Any]:
    root=root.resolve(); config=config or load_config(root); tasks=load_tasks(root)
    errors=validate_assignments(assignments,tasks)
    env=environment_fingerprint(root,config); issues=confounds(root,config,assignments)
    manifest={"schema_version":SCHEMA_VERSION,"created_at":utc_now(),"config":asdict(config),"config_hash":fingerprint(asdict(config)),"tasks":[asdict(t) for t in tasks],"assignments":[asdict(a) for a in assignments],"environment":env,"confounds":issues,"validation_errors":errors}
    manifest["manifest_hash"]=fingerprint(manifest)
    return manifest


def write_manifest(root: Path, manifest: dict[str, Any]) -> Path:
    path=root/RESULT_NAME; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return path


def verify_manifest(manifest: dict[str, Any]) -> bool:
    expected=manifest.get("manifest_hash")
    if not expected: return False
    copy=dict(manifest); copy.pop("manifest_hash",None)
    return fingerprint(copy)==expected


def package_evidence(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    payload={"manifest":manifest,"manifest_verified":verify_manifest(manifest),"generated_at":utc_now()}
    path=root/".skein"/"experiment-evidence.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"verified":payload["manifest_verified"]}


def render_report(result: dict[str, Any]) -> str:
    a=result["assignments"]; counts={"baseline":sum(x["arm"]=="baseline" for x in a),"skein":sum(x["arm"]=="skein" for x in a)}
    lines=["# Skein v0.6 Experimental Control Plane Report","",f"**Experiment:** {result['config']['experiment_id']}",f"**Tasks:** {len(result['tasks'])}",f"**Assignments:** {len(a)}",f"**Allocation:** baseline={counts['baseline']}, skein={counts['skein']}",f"**Manifest verified:** {'YES' if verify_manifest(result) else 'NO'}","", "## Confounds",""]
    lines += [f"- **{x['severity']}** {x['type']}: {x['detail']}" for x in result["confounds"]]
    if not result["confounds"]: lines.append("- None detected")
    lines += ["", "## Interpretation", "The control plane establishes reproducible assignment and provenance. It does not by itself establish causal impact; execution telemetry and matched outcomes remain required.", ""]
    return "\n".join(lines)


def write_report(root: Path, result: dict[str, Any]) -> Path:
    path=root/REPORT_NAME; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(render_report(result)+"\n",encoding="utf-8"); return path
