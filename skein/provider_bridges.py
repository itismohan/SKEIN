"""Concrete provider execution bridges for Skein v0.7.

The bridges adapt real OpenAI/Anthropic-compatible clients to Skein's provider-neutral
AgentRequest/AgentResult contract. Provider SDKs remain optional: callers may inject
an already-configured client or a small callable. No credentials are read or persisted
by Skein.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Protocol

from .agent_adapters import AgentRequest, AgentResult, persist_result


class ProviderClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


def _get(value: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return default


def _usage(response: Any) -> Any:
    return _get(response, "usage", default={}) or {}


def _text(response: Any) -> str:
    # OpenAI Responses API: output_text is the preferred aggregate text.
    text = _get(response, "output_text", default=None)
    if isinstance(text, str):
        return text
    # Chat Completions: choices[0].message.content
    choices = _get(response, "choices", default=None)
    if choices:
        first = choices[0]
        message = _get(first, "message", default=None)
        content = _get(message, "content", default=None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = []
            for item in content:
                value = _get(item, "text", default=item if isinstance(item, str) else None)
                if isinstance(value, str):
                    chunks.append(value)
            if chunks:
                return "".join(chunks)
    # Anthropic Messages API: content=[TextBlock(...)]
    content = _get(response, "content", default=None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            value = _get(item, "text", default=item if isinstance(item, str) else None)
            if isinstance(value, str):
                chunks.append(value)
        if chunks:
            return "".join(chunks)
    return ""


def _usage_int(usage: Any, *names: str) -> int:
    value = _get(usage, *names, default=0)
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _reasoning_tokens(usage: Any) -> int:
    details = _get(usage, "completion_tokens_details", default=None)
    if details is not None:
        return _usage_int(details, "reasoning_tokens")
    return _usage_int(usage, "reasoning_tokens")


def _model(response: Any, fallback: str | None) -> str | None:
    value = _get(response, "model", default=fallback)
    return str(value) if value is not None else None


class OpenAIExecutionBridge:
    """Execute an AgentRequest through an injected OpenAI-compatible client.

    Supported client shapes include ``client.responses.create`` and
    ``client.chat.completions.create``. The bridge does not import the OpenAI SDK.
    """

    provider = "openai"
    name = "openai-responses"

    def __init__(self, client: Any, *, model: str, api_mode: str = "responses") -> None:
        self.client = client
        self.model = model
        if api_mode not in {"responses", "chat"}:
            raise ValueError("api_mode must be 'responses' or 'chat'")
        self.api_mode = api_mode

    def _call(self, request: AgentRequest) -> Any:
        prompt = f"Task:\n{request.task_description}\n\nContext:\n{request.context}"
        if self.api_mode == "responses":
            create = self.client.responses.create
            return create(model=self.model, input=prompt)
        create = self.client.chat.completions.create
        return create(model=self.model, messages=[{"role": "user", "content": prompt}])

    def invoke(self, request: AgentRequest) -> AgentResult:
        started = time.perf_counter()
        execution_id = __import__("uuid").uuid4().hex
        try:
            response = self._call(request)
            usage = _usage(response)
            return AgentResult(
                execution_id=execution_id, provider=self.provider, agent=request.agent,
                task_id=request.task_id, experiment=request.experiment,
                model=_model(response, self.model), outcome="success",
                input_tokens=_usage_int(usage, "input_tokens", "prompt_tokens"),
                output_tokens=_usage_int(usage, "output_tokens", "completion_tokens"),
                reasoning_tokens=_reasoning_tokens(usage),
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                response=_text(response),
                metadata={"api_mode": self.api_mode},
            )
        except Exception as exc:
            return AgentResult(
                execution_id=execution_id, provider=self.provider, agent=request.agent,
                task_id=request.task_id, experiment=request.experiment, model=self.model,
                outcome="failure", input_tokens=max(0, len(request.context.split())),
                output_tokens=0, reasoning_tokens=0,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(exc), metadata={"api_mode": self.api_mode},
            )


class AnthropicExecutionBridge:
    """Execute an AgentRequest through an injected Anthropic-compatible client."""

    provider = "anthropic"
    name = "anthropic-messages"

    def __init__(self, client: Any, *, model: str, max_tokens: int = 2048) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def invoke(self, request: AgentRequest) -> AgentResult:
        started = time.perf_counter()
        execution_id = __import__("uuid").uuid4().hex
        try:
            prompt = f"Task:\n{request.task_description}\n\nContext:\n{request.context}"
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            usage = _usage(response)
            return AgentResult(
                execution_id=execution_id, provider=self.provider, agent=request.agent,
                task_id=request.task_id, experiment=request.experiment,
                model=_model(response, self.model), outcome="success",
                input_tokens=_usage_int(usage, "input_tokens"),
                output_tokens=_usage_int(usage, "output_tokens"), reasoning_tokens=0,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                response=_text(response), metadata={"max_tokens": self.max_tokens},
            )
        except Exception as exc:
            return AgentResult(
                execution_id=execution_id, provider=self.provider, agent=request.agent,
                task_id=request.task_id, experiment=request.experiment, model=self.model,
                outcome="failure", input_tokens=max(0, len(request.context.split())),
                output_tokens=0, reasoning_tokens=0,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(exc), metadata={"max_tokens": self.max_tokens},
            )


def execute_and_persist(root: Any, adapter: Any, request: AgentRequest) -> AgentResult:
    """Invoke a concrete bridge and persist its normalized evidence event."""
    result = adapter.invoke(request)
    persist_result(root, request, result)
    return result
