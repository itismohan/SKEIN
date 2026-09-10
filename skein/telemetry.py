"""Append-only token/cost telemetry for Skein-routed agent operations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
from typing import Iterable


@dataclass(frozen=True)
class AgentCall:
    call_id: str
    timestamp: str
    repo: str
    team: str
    agent: str
    lifecycle_stage: str
    operation: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None = None
    estimated_cost_usd: float | None = None
    outcome: str = "success"
    metadata: dict[str, object] | None = None


class TelemetryStore:
    """Durable JSONL telemetry store adjacent to the versioned graph history."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = root / "agent_calls.jsonl"

    def append(self, event: AgentCall) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def log(
        self,
        *,
        repo: str,
        team: str,
        agent: str,
        lifecycle_stage: str,
        operation: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        reasoning_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        outcome: str = "success",
        metadata: dict[str, object] | None = None,
    ) -> AgentCall:
        timestamp = datetime.now(timezone.utc).isoformat()
        material = {"timestamp": timestamp, "repo": repo, "team": team, "agent": agent,
                    "operation": operation, "input_tokens": input_tokens,
                    "output_tokens": output_tokens}
        call_id = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()[:16]
        event = AgentCall(call_id, timestamp, repo, team, agent, lifecycle_stage, operation,
                          input_tokens, output_tokens, reasoning_tokens, estimated_cost_usd,
                          outcome, metadata or {})
        self.append(event)
        return event

    def events(self) -> list[AgentCall]:
        if not self.path.exists():
            return []
        return [AgentCall(**json.loads(line)) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def aggregate(self, *, repo: str | None = None, team: str | None = None) -> dict[str, object]:
        events = self.events()
        if repo:
            events = [e for e in events if e.repo == repo]
        if team:
            events = [e for e in events if e.team == team]
        by_stage: dict[str, dict[str, float]] = {}
        for e in events:
            row = by_stage.setdefault(e.lifecycle_stage, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cost_usd": 0.0})
            row["calls"] += 1
            row["input_tokens"] += e.input_tokens
            row["output_tokens"] += e.output_tokens
            row["reasoning_tokens"] += e.reasoning_tokens or 0
            row["cost_usd"] += e.estimated_cost_usd or 0.0
        return {"events": len(events), "by_stage": by_stage}
