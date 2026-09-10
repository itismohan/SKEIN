import json
from pathlib import Path

from skein.connector import AnthropicConnector, OpenAIConnector, ingest_events, summarize


def test_openai_usage_normalizes(tmp_path: Path):
    result = ingest_events(tmp_path, [{"event_id": "e1", "model": "gpt-test", "usage": {"prompt_tokens": 100, "completion_tokens": 40}, "outcome": "success"}], provider="openai", experiment="skein", task_id="t1", agent="coder")
    assert result["imported"] == 1
    row = json.loads((tmp_path / ".skein/history/connector-events.jsonl").read_text())
    assert row["input_tokens"] == 100 and row["output_tokens"] == 40 and row["provider"] == "openai"


def test_duplicate_events_are_idempotent(tmp_path: Path):
    payload = [{"event_id": "e1", "usage": {"input_tokens": 10, "output_tokens": 5}}]
    assert ingest_events(tmp_path, payload, provider="generic", experiment="baseline", task_id="t1", agent="planner")["imported"] == 1
    assert ingest_events(tmp_path, payload, provider="generic", experiment="baseline", task_id="t1", agent="planner")["duplicates"] == 1


def test_anthropic_usage_and_summary(tmp_path: Path):
    event = AnthropicConnector().normalize({"event_id": "a1", "model": "claude-test", "usage": {"input_tokens": 20, "output_tokens": 8}}, experiment="baseline", task_id="t2", agent="reviewer")
    assert event.input_tokens == 20 and event.output_tokens == 8 and event.provider == "anthropic"
    ingest_events(tmp_path, [{"event_id": "a1", "usage": {"input_tokens": 20, "output_tokens": 8}}], provider="anthropic", experiment="baseline", task_id="t2", agent="reviewer")
    assert summarize(tmp_path)["tasks"] == 1
