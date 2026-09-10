import json
from pathlib import Path

from skein.agent_adapters import AgentRequest, AnthropicAdapter, OpenAIAdapter, persist_result


def request():
    return AgentRequest("T1", "baseline", "coding-agent", "fix checkout", "checkout dependency context")


def test_openai_adapter_normalizes_injected_response(tmp_path: Path):
    adapter = OpenAIAdapter(lambda r: {
        "event_id": "evt-openai-1", "model": "gpt-test",
        "usage": {"prompt_tokens": 12, "completion_tokens": 8,
                   "completion_tokens_details": {"reasoning_tokens": 3}},
        "outcome": "success", "response": "done"
    })
    result = adapter.invoke(request())
    assert result.provider == "openai"
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    assert result.reasoning_tokens == 3
    assert result.outcome == "success"
    persist_result(tmp_path, request(), result)
    rows = (tmp_path/".skein/history/connector-events.jsonl").read_text().splitlines()
    assert json.loads(rows[-1])["event_type"] == "agent_adapter_execution"


def test_anthropic_adapter_normalizes_usage(tmp_path: Path):
    adapter = AnthropicAdapter(lambda r: {
        "event_id": "evt-anthropic-1", "model": "claude-test",
        "usage": {"input_tokens": 15, "output_tokens": 6}, "outcome": "success"
    })
    result = adapter.invoke(request())
    assert result.provider == "anthropic"
    assert result.input_tokens == 15
    assert result.output_tokens == 6
    assert result.outcome == "success"


def test_adapter_failure_is_recorded():
    result = OpenAIAdapter(lambda r: (_ for _ in ()).throw(RuntimeError("provider unavailable"))).invoke(request())
    assert result.outcome == "failure"
    assert "provider unavailable" in (result.error or "")

class _Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _OpenAIResponses:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return _Obj(
            model=kwargs["model"],
            output_text="implemented",
            usage=_Obj(input_tokens=21, output_tokens=9, completion_tokens_details=_Obj(reasoning_tokens=2)),
        )


class _OpenAIClient:
    def __init__(self): self.responses = _OpenAIResponses()


class _AnthropicMessages:
    def create(self, **kwargs):
        return _Obj(model=kwargs["model"], content=[_Obj(text="done")], usage=_Obj(input_tokens=17, output_tokens=5))


class _AnthropicClient:
    def __init__(self): self.messages = _AnthropicMessages()


def test_openai_execution_bridge_calls_responses_and_normalizes():
    from skein.provider_bridges import OpenAIExecutionBridge
    result = OpenAIExecutionBridge(_OpenAIClient(), model="gpt-test").invoke(request())
    assert result.provider == "openai"
    assert result.model == "gpt-test"
    assert result.response == "implemented"
    assert result.input_tokens == 21
    assert result.output_tokens == 9
    assert result.reasoning_tokens == 2
    assert result.outcome == "success"


def test_anthropic_execution_bridge_calls_messages_and_normalizes():
    from skein.provider_bridges import AnthropicExecutionBridge
    result = AnthropicExecutionBridge(_AnthropicClient(), model="claude-test").invoke(request())
    assert result.provider == "anthropic"
    assert result.response == "done"
    assert result.input_tokens == 17
    assert result.output_tokens == 5
    assert result.outcome == "success"
