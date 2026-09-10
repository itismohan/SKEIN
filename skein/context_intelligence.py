"""Adaptive Context Intelligence for Skein v0.8.

Ranks graph evidence for an agent task instead of returning a fixed structural
context. The scorer is deterministic, explainable, budget-aware, and learns from
persisted feedback without requiring an external vector database or model.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .store import LocalGraphStore

SCHEMA_VERSION = "0.8.0"
FEEDBACK_NAME = ".skein/history/context-feedback.jsonl"
SELECTION_NAME = ".skein/history/context-selections.jsonl"
TOKEN_BUDGET = 1200
_WORD = re.compile(r"[A-Za-z0-9_:$.-]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _words(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text) if len(w) > 1}


def _node_text(node: str, data: dict[str, Any]) -> str:
    attrs = data.get("attributes", {}) or {}
    parts = [node, data.get("type", ""), attrs.get("name", ""), attrs.get("qualified_name", ""), attrs.get("path", ""), attrs.get("text", "")]
    return " ".join(str(x) for x in parts if x)


def _tokens(text: str) -> int:
    return len(text.split())


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class ContextCandidate:
    node_id: str
    node_type: str
    score: float
    lexical_score: float
    graph_score: float
    feedback_score: float
    reason: tuple[str, ...]
    token_cost: int
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextSelection:
    schema_version: str
    task_id: str
    query: str
    budget_tokens: int
    selected: tuple[ContextCandidate, ...]
    total_tokens: int
    strategy: str = "adaptive-v1"
    selection_id: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "query": self.query,
            "budget_tokens": self.budget_tokens,
            "selected": [x.to_dict() for x in self.selected],
            "total_tokens": self.total_tokens,
            "strategy": self.strategy,
            "selection_id": self.selection_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ContextFeedback:
    selection_id: str
    node_id: str
    reward: float
    task_id: str = ""
    reason: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FeedbackStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / FEEDBACK_NAME

    def append(self, feedback: ContextFeedback) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(feedback.to_dict(), sort_keys=True) + "\n")

    def scores(self) -> dict[str, float]:
        result: dict[str, list[float]] = {}
        if not self.path.exists():
            return {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            result.setdefault(row["node_id"], []).append(float(row["reward"]))
        # Bounded empirical prior. Positive feedback can lift evidence, negative
        # feedback can suppress it, but history can never dominate task relevance.
        return {node: max(-1.0, min(1.0, sum(vals) / len(vals))) for node, vals in result.items()}


class AdaptiveContextEngine:
    """Deterministic adaptive selector over the existing Skein graph."""

    def __init__(self, root: Path, *, budget_tokens: int = TOKEN_BUDGET) -> None:
        self.root = root.resolve()
        self.budget_tokens = budget_tokens
        if budget_tokens <= 0:
            raise ValueError("budget_tokens must be positive")
        graph_path = self.root / ".skein" / "graph.json"
        if not graph_path.exists():
            raise ValueError("Skein graph not found; ingest the repository first")
        self.store = LocalGraphStore.load(graph_path)
        self.feedback = FeedbackStore(self.root)

    def _candidate_pool(self, query: str) -> list[ContextCandidate]:
        qwords = _words(query)
        feedback = self.feedback.scores()
        candidates: list[ContextCandidate] = []
        graph = self.store.graph
        for node, data in graph.nodes(data=True):
            text = _node_text(str(node), data)
            words = _words(text)
            overlap = len(qwords & words)
            lexical = overlap / max(1, len(qwords))
            if lexical <= 0:
                # Exact qualified/name fragments still count even when tokenized oddly.
                if any(part and part.lower() in text.lower() for part in query.split() if len(part) > 2):
                    lexical = 0.15
                else:
                    continue
            degree = graph.degree(node)
            graph_score = min(1.0, math.log1p(degree) / 5.0)
            fb = feedback.get(str(node), 0.0)
            score = (0.72 * lexical) + (0.18 * graph_score) + (0.10 * max(-1.0, fb))
            reason = [f"lexical={lexical:.3f}", f"degree={degree}"]
            if fb:
                reason.append(f"feedback={fb:.3f}")
            token_cost = max(1, _tokens(text))
            candidates.append(ContextCandidate(str(node), str(data.get("type", "Unknown")), round(score, 6), round(lexical, 6), round(graph_score, 6), round(fb, 6), tuple(reason), token_cost, 0))
        return sorted(candidates, key=lambda x: (-x.score, x.token_cost, x.node_id))

    def select(self, task_id: str, query: str, *, budget_tokens: int | None = None) -> ContextSelection:
        budget = budget_tokens or self.budget_tokens
        if budget <= 0:
            raise ValueError("budget_tokens must be positive")
        candidates = self._candidate_pool(query)
        selected: list[ContextCandidate] = []
        used = 0
        seen_types: set[str] = set()
        # Diversity bonus is implemented as a greedy selection step: once a node
        # type is represented, prefer a new type when scores are close.
        remaining = candidates[:]
        while remaining:
            best = None
            best_value = -float("inf")
            for c in remaining:
                if used + c.token_cost > budget:
                    continue
                diversity = 0.035 if c.node_type not in seen_types else 0.0
                value = c.score + diversity
                if value > best_value:
                    best_value, best = value, c
            if best is None:
                break
            selected.append(best)
            used += best.token_cost
            seen_types.add(best.node_type)
            remaining.remove(best)
        payload = {"task_id": task_id, "query": query, "budget": budget, "selected": [x.node_id for x in selected]}
        selection_id = _fingerprint(payload)[:24]
        result = ContextSelection(SCHEMA_VERSION, task_id, query, budget, tuple(selected), used, selection_id=selection_id, created_at=_now())
        self._persist_selection(result)
        return result

    def render(self, selection: ContextSelection) -> str:
        lines = [f"Adaptive Skein context (budget={selection.budget_tokens}, used={selection.total_tokens}):"]
        for c in selection.selected:
            data = self.store.graph.nodes[c.node_id]
            attrs = data.get("attributes", {}) or {}
            label = attrs.get("qualified_name") or attrs.get("name") or c.node_id
            lines.append(f"- [{c.node_type}] {label} :: score={c.score:.3f} ({', '.join(c.reason)})")
        return "\n".join(lines)

    def feedback_event(self, selection_id: str, node_id: str, reward: float, *, task_id: str = "", reason: str = "") -> ContextFeedback:
        if not -1.0 <= reward <= 1.0:
            raise ValueError("reward must be between -1 and 1")
        event = ContextFeedback(selection_id, node_id, reward, task_id, reason, _now())
        self.feedback.append(event)
        return event

    def _persist_selection(self, selection: ContextSelection) -> None:
        path = self.root / SELECTION_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(selection.to_dict(), sort_keys=True) + "\n")


def context_health(root: Path) -> dict[str, Any]:
    root = root.resolve()
    fs = FeedbackStore(root)
    scores = fs.scores()
    path = root / SELECTION_NAME
    selections = 0 if not path.exists() else sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return {"schema_version": SCHEMA_VERSION, "selections": selections, "feedback_nodes": len(scores), "adaptive_nodes": sum(1 for v in scores.values() if v != 0)}
