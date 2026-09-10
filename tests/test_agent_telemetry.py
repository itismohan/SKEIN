import json
from pathlib import Path
import pytest
from skein.agent_telemetry import import_jsonl, summarize_tasks


def test_import_and_pair_tasks(tmp_path: Path):
    source = tmp_path / "events.jsonl"
    rows = [
        {"event_id":"b1","experiment":"baseline","task_id":"T1","agent":"coder","timestamp":"2026-01-01T00:00:00Z","input_tokens":100,"output_tokens":20,"estimated_cost_usd":1.0,"outcome":"success"},
        {"event_id":"s1","experiment":"skein","task_id":"T1","agent":"coder","timestamp":"2026-01-01T00:01:00Z","input_tokens":60,"output_tokens":12,"estimated_cost_usd":0.6,"outcome":"success","handoff_to":"reviewer"},
    ]
    source.write_text("\n".join(json.dumps(r) for r in rows))
    assert import_jsonl(tmp_path, source)["imported"] == 2
    summary = summarize_tasks(tmp_path)
    assert summary["paired_tasks"] == 1
    assert summary["tasks"][0]["tokens"] == 192
    assert summary["tasks"][0]["handoffs"] == 1


def test_import_rejects_duplicate_event_ids(tmp_path: Path):
    source = tmp_path / "events.jsonl"
    row = {"event_id":"x","experiment":"baseline","task_id":"T1","agent":"a","timestamp":"now"}
    source.write_text(json.dumps(row)+"\n"+json.dumps(row))
    with pytest.raises(ValueError, match="duplicate"):
        import_jsonl(tmp_path, source)
