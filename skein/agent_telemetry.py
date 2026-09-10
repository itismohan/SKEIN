"""Provider-neutral agent telemetry ingestion for Skein pilot experiments.

The adapter accepts normalized JSONL events from external runners. It never requires a
specific model provider and preserves raw event IDs/metadata so pilot evidence remains auditable.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .telemetry import TelemetryStore

EVENT_SCHEMA_VERSION = "0.4.0"


@dataclass(frozen=True)
class AgentTelemetryRecord:
    event_id: str
    experiment: str
    task_id: str
    agent: str
    lifecycle_stage: str
    operation: str
    timestamp: str
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: float | None = None
    latency_ms: float | None = None
    outcome: str = "unknown"
    handoff_from: str | None = None
    handoff_to: str | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTelemetryRecord":
        required = ["event_id", "experiment", "task_id", "agent", "timestamp"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"missing required telemetry fields: {', '.join(missing)}")
        experiment = str(data["experiment"]).lower()
        if experiment not in {"baseline", "skein"}:
            raise ValueError("experiment must be 'baseline' or 'skein'")
        return cls(
            event_id=str(data["event_id"]), experiment=experiment, task_id=str(data["task_id"]),
            agent=str(data["agent"]), lifecycle_stage=str(data.get("lifecycle_stage", "unknown")),
            operation=str(data.get("operation", "unknown")), timestamp=str(data["timestamp"]),
            input_tokens=max(0, int(data.get("input_tokens", 0))),
            output_tokens=max(0, int(data.get("output_tokens", 0))),
            reasoning_tokens=max(0, int(data.get("reasoning_tokens", 0))),
            estimated_cost_usd=(float(data["estimated_cost_usd"]) if data.get("estimated_cost_usd") is not None else None),
            latency_ms=(float(data["latency_ms"]) if data.get("latency_ms") is not None else None),
            outcome=str(data.get("outcome", "unknown")),
            handoff_from=(str(data["handoff_from"]) if data.get("handoff_from") is not None else None),
            handoff_to=(str(data["handoff_to"]) if data.get("handoff_to") is not None else None),
            metadata=dict(data.get("metadata") or {}),
        )


def read_jsonl(path: Path) -> list[AgentTelemetryRecord]:
    records: list[AgentTelemetryRecord] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = AgentTelemetryRecord.from_dict(json.loads(line))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise ValueError(f"invalid telemetry at line {number}: {exc}") from exc
        if record.event_id in seen:
            raise ValueError(f"duplicate telemetry event_id: {record.event_id}")
        seen.add(record.event_id)
        records.append(record)
    return records


def import_jsonl(root: Path, source: Path) -> dict[str, Any]:
    records = read_jsonl(source)
    store = TelemetryStore(root / ".skein" / "history")
    imported = 0
    for record in records:
        metadata = dict(record.metadata or {})
        metadata.update({
            "experiment": record.experiment,
            "task_id": record.task_id,
            "event_id": record.event_id,
            "handoff_from": record.handoff_from,
            "handoff_to": record.handoff_to,
            "telemetry_schema": EVENT_SCHEMA_VERSION,
        })
        store.log(
            repo=str(root), team="pilot", agent=record.agent,
            lifecycle_stage=record.lifecycle_stage, operation=record.operation,
            input_tokens=record.input_tokens, output_tokens=record.output_tokens,
            reasoning_tokens=record.reasoning_tokens,
            estimated_cost_usd=record.estimated_cost_usd,
            outcome=record.outcome, metadata=metadata,
        )
        imported += 1
    return {"schema_version": EVENT_SCHEMA_VERSION, "source": str(source), "imported": imported}


def summarize_tasks(root: Path) -> dict[str, Any]:
    events = TelemetryStore(root / ".skein" / "history").events()
    tasks: dict[str, dict[str, Any]] = {}
    for event in events:
        meta = event.metadata or {}
        task_id = str(meta.get("task_id", ""))
        experiment = str(meta.get("experiment", ""))
        if not task_id or experiment not in {"baseline", "skein"}:
            continue
        row = tasks.setdefault(task_id, {"experiments": set(), "agents": set(), "calls": 0, "tokens": 0, "cost_usd": 0.0, "errors": 0, "handoffs": 0})
        row["experiments"].add(experiment); row["agents"].add(event.agent); row["calls"] += 1
        row["tokens"] += event.input_tokens + event.output_tokens + (event.reasoning_tokens or 0)
        row["cost_usd"] += event.estimated_cost_usd or 0.0
        row["errors"] += int(event.outcome not in {"success", "succeeded"})
        row["handoffs"] += int(bool(meta.get("handoff_from") or meta.get("handoff_to")))
    normalized = []
    for task_id, row in sorted(tasks.items()):
        normalized.append({"task_id": task_id, **{k: sorted(v) if isinstance(v, set) else v for k, v in row.items()}})
    paired = [r for r in normalized if set(r["experiments"]) == {"baseline", "skein"}]
    return {"tasks": normalized, "paired_tasks": len(paired), "total_tasks": len(normalized)}
