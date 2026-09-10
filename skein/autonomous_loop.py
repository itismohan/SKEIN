"""Autonomous Quality Loop for Skein v0.9.

Closes the v0.8 adaptive-context loop: select context -> execute an agent ->
observe the result -> evaluate quality -> feed evidence back -> optionally retry
with a newly selected context. The loop is deliberately bounded, deterministic at
the control-plane level, and auditable. It does not claim that an agent's exit
status proves engineering correctness; callers may inject a real quality evaluator.
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .agent_adapters import AgentAdapter, AgentRequest, AgentResult, persist_result
from .context_intelligence import AdaptiveContextEngine, ContextSelection

SCHEMA_VERSION = "0.9.0"
LOOP_NAME = ".skein/history/quality-loops.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class QualitySignal:
    passed: bool
    score: float
    reason: str = ""
    retryable: bool = True
    checks: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("quality score must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QualityIteration:
    iteration: int
    execution_id: str
    selection_id: str
    context_tokens: int
    outcome: str
    quality: QualitySignal
    feedback_reward: float
    selected_nodes: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "execution_id": self.execution_id,
            "selection_id": self.selection_id,
            "context_tokens": self.context_tokens,
            "outcome": self.outcome,
            "quality": self.quality.to_dict(),
            "feedback_reward": self.feedback_reward,
            "selected_nodes": list(self.selected_nodes),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class QualityLoopResult:
    loop_id: str
    schema_version: str
    task_id: str
    agent: str
    passed: bool
    iterations: tuple[QualityIteration, ...]
    stop_reason: str
    started_at: str
    finished_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "agent": self.agent,
            "passed": self.passed,
            "iterations": [x.to_dict() for x in self.iterations],
            "stop_reason": self.stop_reason,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


QualityEvaluator = Callable[[AgentRequest, AgentResult], QualitySignal]


def default_quality_evaluator(_: AgentRequest, result: AgentResult) -> QualitySignal:
    """Conservative fallback: provider success is execution success, not proof of quality."""
    passed = result.outcome == "success"
    return QualitySignal(
        passed=passed,
        score=1.0 if passed else 0.0,
        reason="agent execution completed" if passed else (result.error or "agent execution failed"),
        retryable=not passed,
        checks={"execution_outcome": result.outcome},
    )


def _append(root: Path, result: QualityLoopResult) -> None:
    path = root / LOOP_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), sort_keys=True) + "\n")


def run_quality_loop(
    root: Path,
    *,
    task_id: str,
    task_description: str,
    adapter: AgentAdapter,
    agent: str = "quality-loop-agent",
    max_iterations: int = 3,
    budget_tokens: int = 1200,
    quality_threshold: float = 1.0,
    evaluator: QualityEvaluator | None = None,
    context_query: str | None = None,
) -> QualityLoopResult:
    """Run a bounded observe/evaluate/learn/retry loop.

    The adapter performs the actual provider invocation. Skein owns context
    selection, feedback, retry policy, and evidence persistence.
    """
    root = root.resolve()
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")
    if not 0.0 <= quality_threshold <= 1.0:
        raise ValueError("quality_threshold must be between 0 and 1")
    engine = AdaptiveContextEngine(root, budget_tokens=budget_tokens)
    evaluate_quality = evaluator or default_quality_evaluator
    started = _now()
    loop_id = _fingerprint({"task_id": task_id, "agent": agent, "started_at": started})
    iterations: list[QualityIteration] = []
    last_selection: ContextSelection | None = None
    stop_reason = "iteration_limit"

    for number in range(1, max_iterations + 1):
        selection = engine.select(task_id, context_query or task_description, budget_tokens=budget_tokens)
        last_selection = selection
        context = engine.render(selection)
        request = AgentRequest(
            task_id=task_id,
            experiment="skein",
            agent=agent,
            task_description=task_description,
            context=context,
            metadata={
                "schema_version": SCHEMA_VERSION,
                "loop_id": loop_id,
                "iteration": number,
                "selection_id": selection.selection_id,
            },
        )
        try:
            result = adapter.invoke(request)
        except Exception as exc:
            result = AgentResult(
                execution_id=_fingerprint({"loop_id": loop_id, "iteration": number, "error": str(exc)}),
                provider=getattr(adapter, "provider", "generic"), agent=agent, task_id=task_id,
                experiment="skein", model=None, outcome="failure",
                input_tokens=len(context.split()), output_tokens=0, reasoning_tokens=0,
                latency_ms=0.0, error=str(exc), metadata={},
            )
        persist_result(root, request, result)
        quality = evaluate_quality(request, result)
        reward = max(-1.0, min(1.0, (quality.score * 2.0) - 1.0))
        if quality.passed and quality.score >= quality_threshold:
            reward = max(reward, 0.5)
        elif not quality.passed:
            reward = min(reward, -0.25)
        for candidate in selection.selected:
            engine.feedback_event(
                selection.selection_id,
                candidate.node_id,
                reward,
                task_id=task_id,
                reason=quality.reason or "quality-loop feedback",
            )
        iterations.append(QualityIteration(
            iteration=number,
            execution_id=result.execution_id,
            selection_id=selection.selection_id,
            context_tokens=selection.total_tokens,
            outcome=result.outcome,
            quality=quality,
            feedback_reward=reward,
            selected_nodes=tuple(x.node_id for x in selection.selected),
            created_at=_now(),
        ))
        if quality.passed and quality.score >= quality_threshold:
            stop_reason = "quality_gate_passed"
            break
        if not quality.retryable:
            stop_reason = "quality_gate_non_retryable"
            break
        if number == max_iterations:
            stop_reason = "iteration_limit"

    finished = _now()
    result = QualityLoopResult(
        loop_id=loop_id,
        schema_version=SCHEMA_VERSION,
        task_id=task_id,
        agent=agent,
        passed=bool(iterations and iterations[-1].quality.passed and iterations[-1].quality.score >= quality_threshold),
        iterations=tuple(iterations),
        stop_reason=stop_reason,
        started_at=started,
        finished_at=finished,
    )
    _append(root, result)
    return result


def quality_loop_summary(root: Path) -> dict[str, Any]:
    path = root.resolve() / LOOP_NAME
    rows = [] if not path.exists() else [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {
        "schema_version": SCHEMA_VERSION,
        "loops": len(rows),
        "passed": sum(1 for x in rows if x.get("passed")),
        "failed": sum(1 for x in rows if not x.get("passed")),
        "iterations": sum(len(x.get("iterations", [])) for x in rows),
        "average_iterations": round(sum(len(x.get("iterations", [])) for x in rows) / len(rows), 3) if rows else 0.0,
    }
