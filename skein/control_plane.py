"""Skein v1.0 AI-DLC Control Plane.

The control plane coordinates specification, graph context, agent execution,
quality evidence, governance, and human approval as one auditable lifecycle.
It is intentionally policy-first: the control plane may recommend or invoke
approved adapters, but it never silently mutates source code or bypasses gates.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .governance.policy import load_policy
from .sdd import load_clauses, validate_clauses

SCHEMA_VERSION = "1.0.0"
CONTROL_LOG = ".skein/history/control-plane.jsonl"
STATE_FILE = ".skein/control-plane.json"

TERMINAL = {"completed", "rejected", "failed", "cancelled"}
ALLOWED_TRANSITIONS = {
    "created": {"planned", "rejected", "cancelled"},
    "planned": {"executing", "rejected", "cancelled"},
    "executing": {"evaluating", "failed", "cancelled"},
    "evaluating": {"approval_required", "completed", "failed", "rejected"},
    "approval_required": {"approved", "rejected", "cancelled"},
    "approved": {"completed", "executing", "cancelled"},
    "completed": set(), "rejected": set(), "failed": set(), "cancelled": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fp(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@dataclass(frozen=True)
class ControlTask:
    task_id: str
    title: str
    description: str
    spec_refs: tuple[str, ...] = ()
    risk: str = "medium"
    required_approval: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["spec_refs"] = list(self.spec_refs)
        return d


@dataclass(frozen=True)
class ControlEvent:
    event_id: str
    run_id: str
    event_type: str
    from_state: str | None
    to_state: str | None
    actor: str
    reason: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlRun:
    run_id: str
    schema_version: str
    task: ControlTask
    state: str
    created_at: str
    updated_at: str
    context_selection_id: str | None = None
    quality_passed: bool | None = None
    quality_score: float | None = None
    execution_id: str | None = None
    approval_actor: str | None = None
    approval_reason: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["task"] = self.task.to_dict()
        return d


class ControlPlane:
    """Persistent lifecycle coordinator over a Skein workspace."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.state_path = self.root / STATE_FILE
        self.log_path = self.root / CONTROL_LOG
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_state(self, run: ControlRun) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _event(self, run: ControlRun, event_type: str, actor: str, reason: str, *, to_state: str | None = None, evidence: Mapping[str, Any] | None = None) -> ControlEvent:
        event = ControlEvent(
            event_id=_fp({"run": run.run_id, "type": event_type, "at": _now(), "actor": actor}),
            run_id=run.run_id, event_type=event_type, from_state=run.state,
            to_state=to_state, actor=actor, reason=reason, evidence=evidence or {}, created_at=_now(),
        )
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return event

    def _authorize(self, actor: str, action: str) -> None:
        policy = load_policy(self.root / ".skein" / "policy.json")
        if not policy.allowed(actor, action):
            raise PermissionError(f"identity {actor!r} is not authorized for {action}")

    def _preflight(self, task: ControlTask) -> dict[str, Any]:
        checks: dict[str, Any] = {}
        graph = self.root / ".skein" / "graph.json"
        checks["graph_present"] = graph.exists()
        if graph.exists():
            checks["graph_sha256"] = hashlib.sha256(graph.read_bytes()).hexdigest()
        clauses_dir = self.root / "spec" / "clauses"
        if clauses_dir.exists():
            clauses = load_clauses(clauses_dir)
            validate_clauses(clauses)
            known = {getattr(c, "clause_id", getattr(c, "id", "")) for c in clauses}
            missing = [ref for ref in task.spec_refs if ref not in known]
            if missing:
                raise ValueError("unknown SDD clause refs: " + ", ".join(missing))
            checks["sdd_clauses"] = len(clauses)
        else:
            checks["sdd_clauses"] = 0
        checks["risk"] = task.risk
        checks["approval_required"] = task.required_approval
        return checks

    def create(self, task: ControlTask, *, actor: str = "local-admin") -> ControlRun:
        self._authorize(actor, "propose")
        if task.risk not in {"low", "medium", "high", "critical"}:
            raise ValueError("risk must be low, medium, high, or critical")
        run_id = _fp({"task": task.to_dict(), "created": _now()})
        now = _now()
        run = ControlRun(run_id, SCHEMA_VERSION, task, "created", now, now)
        self._write_state(run)
        self._event(run, "run_created", actor, "AI-DLC control-plane run created")
        return run

    def get(self) -> ControlRun:
        if not self.state_path.exists():
            raise ValueError("no active control-plane run; initialize one first")
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        task_data = data["task"]
        task = ControlTask(task_data["task_id"], task_data["title"], task_data["description"], tuple(task_data.get("spec_refs", [])), task_data.get("risk", "medium"), bool(task_data.get("required_approval", True)), task_data.get("metadata", {}))
        return ControlRun(data["run_id"], data["schema_version"], task, data["state"], data["created_at"], data["updated_at"], data.get("context_selection_id"), data.get("quality_passed"), data.get("quality_score"), data.get("execution_id"), data.get("approval_actor"), data.get("approval_reason"), data.get("evidence", {}))

    def transition(self, target: str, *, actor: str, reason: str, evidence: Mapping[str, Any] | None = None) -> ControlRun:
        run = self.get()
        if target not in ALLOWED_TRANSITIONS.get(run.state, set()):
            raise ValueError(f"invalid control-plane transition: {run.state} -> {target}")
        updated = replace(run, updated_at=_now(), state=target)
        self._write_state(updated)
        self._event(updated, "state_transition", actor, reason, to_state=target, evidence=evidence)
        return updated

    def plan(self, *, actor: str = "local-admin") -> ControlRun:
        self._authorize(actor, "propose")
        run = self.get()
        checks = self._preflight(run.task)
        return self.transition("planned", actor=actor, reason="task admitted to AI-DLC control plane", evidence=checks)

    def begin_execution(self, *, actor: str = "local-admin", selection_id: str | None = None) -> ControlRun:
        run = self.transition("executing", actor=actor, reason="approved execution phase started", evidence={"selection_id": selection_id} if selection_id else {})
        if selection_id:
            run = replace(run, context_selection_id=selection_id)
            self._write_state(run)
        return run

    def record_evaluation(self, *, passed: bool, score: float, execution_id: str | None = None, actor: str = "quality-gate", evidence: Mapping[str, Any] | None = None) -> ControlRun:
        if not 0.0 <= score <= 1.0:
            raise ValueError("quality score must be between 0 and 1")
        run = self.transition("evaluating", actor=actor, reason="engineering quality evidence recorded", evidence=evidence)
        target = "completed" if passed and not run.task.required_approval else ("approval_required" if passed else "failed")
        run = replace(run, quality_passed=passed, quality_score=score, execution_id=execution_id, updated_at=_now())
        self._write_state(run)
        self._event(run, "quality_evaluated", actor, "quality gate evaluated", to_state=target, evidence={"passed": passed, "score": score, **(dict(evidence or {}))})
        if target != run.state:
            run = replace(run, state=target, updated_at=_now())
            self._write_state(run)
        return run

    def approve(self, *, actor: str, reason: str) -> ControlRun:
        self._authorize(actor, "commit")
        run = self.get()
        if run.state != "approval_required":
            raise ValueError("approval is only valid when approval_required")
        if not actor:
            raise ValueError("approval actor is required")
        updated = replace(run, state="approved", approval_actor=actor, approval_reason=reason, updated_at=_now())
        self._write_state(updated)
        self._event(updated, "human_approval", actor, reason, to_state="approved", evidence={"approval_actor": actor})
        return updated

    def finalize(self, *, actor: str = "local-admin") -> ControlRun:
        self._authorize(actor, "commit")
        run = self.get()
        if run.state != "approved":
            raise ValueError("finalize requires an approved run")
        return self.transition("completed", actor=actor, reason="approved AI-DLC run finalized")

    def reject(self, *, actor: str, reason: str) -> ControlRun:
        run = self.get()
        if "rejected" not in ALLOWED_TRANSITIONS.get(run.state, set()):
            raise ValueError(f"cannot reject run from state {run.state}")
        return self.transition("rejected", actor=actor, reason=reason)

    def status(self) -> dict[str, Any]:
        run = self.get()
        events = []
        if self.log_path.exists():
            events = [json.loads(x) for x in self.log_path.read_text(encoding="utf-8").splitlines() if x.strip() and json.loads(x).get("run_id") == run.run_id]
        return {"schema_version": SCHEMA_VERSION, "run": run.to_dict(), "event_count": len(events), "terminal": run.state in TERMINAL}

    def export(self) -> dict[str, Any]:
        run = self.get()
        events = [] if not self.log_path.exists() else [json.loads(x) for x in self.log_path.read_text(encoding="utf-8").splitlines() if x.strip() and json.loads(x).get("run_id") == run.run_id]
        return {"schema_version": SCHEMA_VERSION, "run": run.to_dict(), "events": events, "integrity": _fp(events)}
