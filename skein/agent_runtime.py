"""Controlled real-agent execution for Skein v0.7.

The runtime executes an explicitly supplied argv command without a shell, injects a
reproducible task/context envelope, captures process telemetry, and persists an
execution record. It is provider-neutral: real provider SDKs can use the connector
SDK, while CLI coding agents can use this runner directly.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from .connector import ConnectorEvent, ConnectorEventStore, _now
from .experiment import Assignment, TaskSpec, load_tasks
from .store import LocalGraphStore
from .query import query as graph_query

SCHEMA_VERSION = "0.7.0"
EXECUTIONS_NAME = ".skein/history/agent-executions.jsonl"
RESULTS_NAME = ".skein/connector-task-results.json"


@dataclass(frozen=True)
class ExecutionRequest:
    task_id: str
    arm: str
    command: tuple[str, ...]
    context_query: str | None = None
    timeout_seconds: float = 300.0
    working_directory: str | None = None
    agent: str = "cli-agent"


@dataclass(frozen=True)
class ExecutionRecord:
    execution_id: str
    schema_version: str
    task_id: str
    experiment: str
    agent: str
    started_at: str
    finished_at: str
    exit_code: int | None
    outcome: str
    latency_ms: float
    context_tokens: int
    task_tokens: int
    stdout_bytes: int
    stderr_bytes: int
    timed_out: bool
    command_fingerprint: str
    context_fingerprint: str
    task_fingerprint: str
    context_mode: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tokens(text: str) -> int:
    return len(text.split())


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_assignment(root: Path, task_id: str) -> list[Assignment]:
    path = root / ".skein" / "experiment-results.json"
    if not path.exists():
        raise ValueError("no experiment assignment found; run skein experiment-assign first")
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = [row for row in data.get("assignments", []) if row.get("task_id") == task_id]
    if not matches:
        raise ValueError(f"task {task_id!r} has no experiment assignment")
    return [Assignment(**row) for row in matches]


def load_task(root: Path, task_id: str) -> TaskSpec:
    for task in load_tasks(root):
        if task.task_id == task_id:
            return task
    raise ValueError(f"unknown experiment task: {task_id!r}")


def build_context(root: Path, task: TaskSpec, arm: str, context_query: str | None = None) -> tuple[str, str]:
    if arm == "baseline":
        return task.description, "baseline"
    if arm != "skein":
        raise ValueError("arm must be 'baseline' or 'skein'")
    graph_path = root / ".skein" / "graph.json"
    if not graph_path.exists():
        raise ValueError("Skein arm requires .skein/graph.json")
    graph = LocalGraphStore.load(graph_path)
    query_text = context_query or task.description
    structural = graph_query(graph, query_text)
    return f"Task:\n{task.description}\n\nSkein context:\n{structural}", "skein"


def _append_execution(root: Path, record: ExecutionRecord) -> None:
    path = root / EXECUTIONS_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")


def _upsert_task_result(root: Path, record: ExecutionRecord) -> None:
    path = root / RESULTS_NAME
    rows: list[dict[str, Any]] = []
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = [r for r in data.get("results", []) if r.get("task_id") != record.task_id or r.get("experiment") != record.experiment]
    rows.append({
        "task_id": record.task_id,
        "experiment": record.experiment,
        "input_tokens": record.context_tokens,
        "context_tokens": record.context_tokens,
        "latency_ms": record.latency_ms,
        "cost_usd": 0.0,
        "outcome": record.outcome,
        "success": record.outcome == "success",
        "rework": 0,
        "handoff_loss": 0,
        "execution_id": record.execution_id,
    })
    rows.sort(key=lambda r: (r["task_id"], r["experiment"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "results": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(root: Path, request: ExecutionRequest, *, env_extra: dict[str, str] | None = None) -> ExecutionRecord:
    root = root.resolve()
    if not request.command or any(not isinstance(x, str) or not x for x in request.command):
        raise ValueError("command must be a non-empty argv sequence")
    if request.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    assignments = load_assignment(root, request.task_id)
    assignment = next((a for a in assignments if a.arm == request.arm), None)
    if assignment is None:
        allowed = ", ".join(sorted(a.arm for a in assignments))
        raise ValueError(f"task {request.task_id!r} has no assignment for arm {request.arm!r}; available: {allowed}")
    task = load_task(root, request.task_id)
    context, context_mode = build_context(root, task, request.arm, request.context_query)
    envelope = json.dumps({"task_id": task.task_id, "description": task.description, "context": context}, ensure_ascii=False)
    env = os.environ.copy()
    env.update({
        "SKEIN_TASK_ID": task.task_id,
        "SKEIN_EXPERIMENT_ARM": request.arm,
        "SKEIN_CONTEXT_MODE": context_mode,
        "SKEIN_TASK_DESCRIPTION": task.description,
        "SKEIN_CONTEXT": context,
        "SKEIN_TASK_CONTEXT_JSON": envelope,
    })
    if env_extra:
        env.update(env_extra)
    cwd = Path(request.working_directory).resolve() if request.working_directory else root
    if not cwd.exists() or not cwd.is_dir():
        raise ValueError(f"working directory does not exist: {cwd}")
    started = _now()
    t0 = time.perf_counter()
    execution_id = uuid.uuid4().hex
    exit_code: int | None = None
    stdout = b""
    stderr = b""
    timed_out = False
    error: str | None = None
    try:
        completed = subprocess.run(
            list(request.command), cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=request.timeout_seconds, shell=False, check=False,
        )
        exit_code = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        error = f"agent command timed out after {request.timeout_seconds}s"
    except OSError as exc:
        error = f"agent command could not start: {exc}"
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    outcome = "success" if exit_code == 0 and not timed_out and error is None else "failure"
    finished = _now()
    record = ExecutionRecord(
        execution_id=execution_id, schema_version=SCHEMA_VERSION, task_id=task.task_id,
        experiment=request.arm, agent=request.agent, started_at=started, finished_at=finished,
        exit_code=exit_code, outcome=outcome, latency_ms=latency_ms,
        context_tokens=_tokens(context), task_tokens=_tokens(task.description),
        stdout_bytes=len(stdout), stderr_bytes=len(stderr), timed_out=timed_out,
        command_fingerprint=_fingerprint(list(request.command)), context_fingerprint=_fingerprint(context),
        task_fingerprint=_fingerprint(task.description), context_mode=context_mode, error=error,
    )
    _append_execution(root, record)
    _upsert_task_result(root, record)
    ConnectorEventStore(root).append(ConnectorEvent(
        event_id=execution_id, task_id=task.task_id, experiment=request.arm, agent=request.agent,
        event_type="agent_execution", timestamp=finished, provider="generic", lifecycle_stage="execution",
        operation="cli_agent", input_tokens=record.context_tokens, output_tokens=0,
        latency_ms=record.latency_ms, estimated_cost_usd=0.0, outcome=outcome,
        metadata={"schema_version": SCHEMA_VERSION, "exit_code": exit_code, "stdout_bytes": len(stdout),
                  "stderr_bytes": len(stderr), "timed_out": timed_out, "context_mode": context_mode,
                  "context_fingerprint": record.context_fingerprint},
    ))
    return record


def execution_summary(root: Path) -> dict[str, Any]:
    path = root / EXECUTIONS_NAME
    records = [] if not path.exists() else [ExecutionRecord(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_arm = {"baseline": 0, "skein": 0}
    successes = 0
    for record in records:
        by_arm[record.experiment] = by_arm.get(record.experiment, 0) + 1
        successes += int(record.outcome == "success")
    return {"schema_version": SCHEMA_VERSION, "executions": len(records), "successes": successes, "by_arm": by_arm}
