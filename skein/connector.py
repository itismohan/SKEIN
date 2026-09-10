"""Provider-neutral agent connector SDK for Skein v0.4.

Connectors normalize provider/framework-specific callbacks into the append-only Skein
agent telemetry stream. No provider SDK is required; adapters accept plain mappings.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

SCHEMA_VERSION = "0.4.0"
EVENTS_NAME = ".skein/history/connector-events.jsonl"


@dataclass(frozen=True)
class ConnectorEvent:
    event_id: str
    task_id: str
    experiment: str
    agent: str
    event_type: str
    timestamp: str
    provider: str = "unknown"
    model: str | None = None
    lifecycle_stage: str = "unknown"
    operation: str = "unknown"
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost_usd: float | None = None
    latency_ms: float | None = None
    outcome: str = "unknown"
    handoff_from: str | None = None
    handoff_to: str | None = None
    tool_name: str | None = None
    graph_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Connector(Protocol):
    provider: str
    def normalize(self, payload: Mapping[str, Any], *, experiment: str, task_id: str, agent: str) -> ConnectorEvent: ...


def _now() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()


def _int(payload: Mapping[str, Any], key: str) -> int:
    return max(0, int(payload.get(key, 0) or 0))


class GenericConnector:
    provider = "generic"

    def normalize(self, payload: Mapping[str, Any], *, experiment: str, task_id: str, agent: str) -> ConnectorEvent:
        if experiment not in {"baseline", "skein"}:
            raise ValueError("experiment must be 'baseline' or 'skein'")
        event_type = str(payload.get("event_type", payload.get("type", "agent_call")))
        return ConnectorEvent(
            event_id=str(payload.get("event_id") or uuid.uuid4().hex), task_id=task_id,
            experiment=experiment, agent=agent, event_type=event_type,
            timestamp=str(payload.get("timestamp") or _now()), provider=self.provider,
            model=str(payload["model"]) if payload.get("model") is not None else None,
            lifecycle_stage=str(payload.get("lifecycle_stage", "unknown")),
            operation=str(payload.get("operation", "unknown")), input_tokens=_int(payload, "input_tokens"),
            output_tokens=_int(payload, "output_tokens"), reasoning_tokens=_int(payload, "reasoning_tokens"),
            estimated_cost_usd=float(payload["estimated_cost_usd"]) if payload.get("estimated_cost_usd") is not None else None,
            latency_ms=float(payload["latency_ms"]) if payload.get("latency_ms") is not None else None,
            outcome=str(payload.get("outcome", "unknown")),
            handoff_from=str(payload["handoff_from"]) if payload.get("handoff_from") is not None else None,
            handoff_to=str(payload["handoff_to"]) if payload.get("handoff_to") is not None else None,
            tool_name=str(payload["tool_name"]) if payload.get("tool_name") is not None else None,
            graph_version=str(payload["graph_version"]) if payload.get("graph_version") is not None else None,
            metadata=dict(payload.get("metadata") or {}),
        )


class OpenAIConnector(GenericConnector):
    provider = "openai"

    def normalize(self, payload: Mapping[str, Any], *, experiment: str, task_id: str, agent: str) -> ConnectorEvent:
        usage = payload.get("usage") or {}
        normalized = dict(payload)
        normalized["model"] = payload.get("model") or payload.get("response_model")
        normalized["input_tokens"] = usage.get("prompt_tokens", payload.get("input_tokens", 0))
        normalized["output_tokens"] = usage.get("completion_tokens", payload.get("output_tokens", 0))
        normalized["reasoning_tokens"] = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", payload.get("reasoning_tokens", 0))
        return super().normalize(normalized, experiment=experiment, task_id=task_id, agent=agent)


class AnthropicConnector(GenericConnector):
    provider = "anthropic"

    def normalize(self, payload: Mapping[str, Any], *, experiment: str, task_id: str, agent: str) -> ConnectorEvent:
        usage = payload.get("usage") or {}
        normalized = dict(payload)
        normalized["model"] = payload.get("model")
        normalized["input_tokens"] = usage.get("input_tokens", payload.get("input_tokens", 0))
        normalized["output_tokens"] = usage.get("output_tokens", payload.get("output_tokens", 0))
        return super().normalize(normalized, experiment=experiment, task_id=task_id, agent=agent)


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        self._connectors[connector.provider] = connector

    def get(self, provider: str) -> Connector:
        try:
            return self._connectors[provider.lower()]
        except KeyError as exc:
            raise ValueError(f"unknown connector provider: {provider}") from exc

    def providers(self) -> list[str]:
        return sorted(self._connectors)


DEFAULT_REGISTRY = ConnectorRegistry()
DEFAULT_REGISTRY.register(GenericConnector())
DEFAULT_REGISTRY.register(OpenAIConnector())
DEFAULT_REGISTRY.register(AnthropicConnector())


class ConnectorEventStore:
    def __init__(self, root: Path) -> None:
        self.path = root / EVENTS_NAME
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: ConnectorEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    def events(self) -> list[ConnectorEvent]:
        if not self.path.exists():
            return []
        return [ConnectorEvent(**json.loads(line)) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ingest_events(root: Path, payloads: Iterable[Mapping[str, Any]], *, provider: str, experiment: str, task_id: str, agent: str) -> dict[str, Any]:
    connector = DEFAULT_REGISTRY.get(provider)
    store = ConnectorEventStore(root)
    seen = {event.event_id for event in store.events()}
    imported = 0
    duplicates = 0
    for payload in payloads:
        event = connector.normalize(payload, experiment=experiment, task_id=task_id, agent=agent)
        if event.event_id in seen:
            duplicates += 1
            continue
        store.append(event); seen.add(event.event_id); imported += 1
    return {"schema_version": SCHEMA_VERSION, "provider": provider, "imported": imported, "duplicates": duplicates, "total": imported + duplicates}


def read_payload_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid connector JSON at line {line_no}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"connector event at line {line_no} must be an object")
        rows.append(value)
    return rows


def summarize(root: Path) -> dict[str, Any]:
    events = ConnectorEventStore(root).events()
    by_provider: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_task: dict[str, int] = {}
    for event in events:
        by_provider[event.provider] = by_provider.get(event.provider, 0) + 1
        by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
        by_task[event.task_id] = by_task.get(event.task_id, 0) + 1
    return {"schema_version": SCHEMA_VERSION, "events": len(events), "tasks": len(by_task), "by_provider": by_provider, "by_event_type": by_type, "by_task": by_task}
