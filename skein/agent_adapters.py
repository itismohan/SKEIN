"""Provider-neutral agent adapter layer for Skein v0.7.

Adapters separate agent/provider invocation from the Skein execution envelope and
telemetry contract. Provider SDKs remain optional: OpenAI/Anthropic adapters accept
an injected callable, making integration testable without network credentials.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from .connector import DEFAULT_REGISTRY, ConnectorEvent, ConnectorEventStore, _now

SCHEMA_VERSION = "0.7.0"


@dataclass(frozen=True)
class AgentRequest:
    task_id: str
    experiment: str
    agent: str
    task_description: str
    context: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def envelope(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "experiment": self.experiment,
            "agent": self.agent,
            "task_description": self.task_description,
            "context": self.context,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AgentResult:
    execution_id: str
    provider: str
    agent: str
    task_id: str
    experiment: str
    model: str | None
    outcome: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_ms: float
    response: Any = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class AgentAdapter(Protocol):
    """Contract implemented by an executable agent/provider adapter."""

    name: str
    provider: str

    def invoke(self, request: AgentRequest) -> AgentResult:
        ...


def _stable_id(request: AgentRequest) -> str:
    raw = json.dumps(request.envelope(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _tokens(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value.split())
    return len(json.dumps(value, ensure_ascii=False).split())


class CallableAdapter:
    """Base for SDK adapters using an injected provider callable."""

    provider = "generic"
    name = "generic"

    def __init__(self, invoke_fn: Callable[[AgentRequest], Mapping[str, Any]]) -> None:
        self._invoke_fn = invoke_fn

    def invoke(self, request: AgentRequest) -> AgentResult:
        execution_id = _stable_id(request)
        started = time.perf_counter()
        try:
            payload = self._invoke_fn(request)
            if not isinstance(payload, Mapping):
                raise ValueError("adapter callable must return a mapping")
            event = DEFAULT_REGISTRY.get(self.provider).normalize(
                payload, experiment=request.experiment, task_id=request.task_id, agent=request.agent
            )
            latency = float(payload.get("latency_ms", round((time.perf_counter() - started) * 1000, 3)))
            return AgentResult(
                execution_id=execution_id,
                provider=event.provider,
                agent=request.agent,
                task_id=request.task_id,
                experiment=request.experiment,
                model=event.model,
                outcome=event.outcome,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                reasoning_tokens=event.reasoning_tokens,
                latency_ms=latency,
                response=payload.get("response", payload.get("output")),
                metadata=dict(event.metadata),
            )
        except Exception as exc:  # provider errors are recorded, not swallowed silently
            return AgentResult(
                execution_id=execution_id,
                provider=self.provider,
                agent=request.agent,
                task_id=request.task_id,
                experiment=request.experiment,
                model=None,
                outcome="failure",
                input_tokens=_tokens(request.context),
                output_tokens=0,
                reasoning_tokens=0,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(exc),
            )


class OpenAIAdapter(CallableAdapter):
    provider = "openai"
    name = "openai"


class AnthropicAdapter(CallableAdapter):
    provider = "anthropic"
    name = "anthropic"


class GenericSDKAdapter(CallableAdapter):
    name = "generic-sdk"


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AgentAdapter] = {}

    def register(self, adapter: AgentAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def get(self, name: str) -> AgentAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise ValueError(f"unknown agent adapter: {name}") from exc


class CliAgentAdapter:
    """Adapter facade for the controlled argv runtime; no shell is ever used."""

    name = "cli"
    provider = "generic"

    def __init__(self, executor: Callable[..., Any]) -> None:
        self._executor = executor

    def invoke(self, request: AgentRequest, *, command: tuple[str, ...], timeout_seconds: float = 300.0) -> AgentResult:
        from .agent_runtime import ExecutionRequest

        record = self._executor(
            ExecutionRequest(
                task_id=request.task_id,
                arm=request.experiment,
                command=command,
                timeout_seconds=timeout_seconds,
                agent=request.agent,
            )
        )
        return AgentResult(
            execution_id=record.execution_id,
            provider="generic",
            agent=record.agent,
            task_id=record.task_id,
            experiment=record.experiment,
            model=None,
            outcome=record.outcome,
            input_tokens=record.context_tokens,
            output_tokens=0,
            reasoning_tokens=0,
            latency_ms=record.latency_ms,
            metadata={"context_mode": record.context_mode, "exit_code": record.exit_code},
            error=record.error,
        )


def persist_result(root: Any, request: AgentRequest, result: AgentResult) -> ConnectorEvent:
    """Persist one adapter result using the canonical connector telemetry schema."""
    event = ConnectorEvent(
        event_id=result.execution_id,
        task_id=request.task_id,
        experiment=request.experiment,
        agent=request.agent,
        event_type="agent_adapter_execution",
        timestamp=_now(),
        provider=result.provider,
        lifecycle_stage="execution",
        operation="agent_adapter",
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        reasoning_tokens=result.reasoning_tokens,
        latency_ms=result.latency_ms,
        outcome=result.outcome,
        metadata={
            "schema_version": SCHEMA_VERSION,
            "adapter": result.provider,
            "request_fingerprint": _stable_id(request),
            **dict(result.metadata),
        },
    )
    ConnectorEventStore(root).append(event)
    return event
