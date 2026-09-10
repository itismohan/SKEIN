import json
from pathlib import Path

from skein.pilot_intelligence import init_intelligence, run_intelligence, render_report
from skein.telemetry import TelemetryStore


def test_intelligence_not_measured_is_honest(tmp_path: Path):
    (tmp_path / ".skein").mkdir()
    scenarios = {"pilot": "p", "results": [
        {"scenario_id": "S01", "mode": "baseline", "latency_ms": 100, "stdout_tokens": 10, "stderr_tokens": 0},
        {"scenario_id": "S01", "mode": "skein", "latency_ms": 80, "stdout_tokens": 8, "stderr_tokens": 0},
    ]}
    (tmp_path / ".skein" / "pilot-scenario-results.json").write_text(json.dumps(scenarios))
    init_intelligence(tmp_path)
    result = run_intelligence(tmp_path)
    assert result["scenario_execution"]["paired_scenarios"] == 1
    assert result["scorecard"]["latency_reduction"]["value_pct"] == 20.0
    assert result["scorecard"]["llm_cost_reduction"]["status"] == "NOT_MEASURED"
    assert result["quality_signals"]["source"] == "not_measured"
    assert result["evidence_quality"]["production_quality_claim_allowed"] is False


def test_intelligence_uses_provider_telemetry_and_quality(tmp_path: Path):
    history = tmp_path / ".skein" / "history"
    history.mkdir(parents=True)
    telemetry = TelemetryStore(history)
    telemetry.log(repo="r", team="t", agent="a", lifecycle_stage="code", operation="task",
                  input_tokens=1000, output_tokens=200, estimated_cost_usd=10.0,
                  metadata={"experiment": "baseline"})
    telemetry.log(repo="r", team="t", agent="a", lifecycle_stage="code", operation="task",
                  input_tokens=600, output_tokens=120, estimated_cost_usd=6.0,
                  metadata={"experiment": "skein"})
    (tmp_path / ".skein" / "pilot-scenario-results.json").write_text(json.dumps({"results": [
        {"scenario_id": "S01", "mode": "baseline", "latency_ms": 100, "stdout_tokens": 10, "stderr_tokens": 0},
        {"scenario_id": "S01", "mode": "skein", "latency_ms": 80, "stdout_tokens": 8, "stderr_tokens": 0},
    ]}))
    (tmp_path / ".skein" / "pilot-experiment-metrics.json").write_text(json.dumps({
        "metrics": {
            "task_success_rate": {"baseline": 0.8, "skein": 0.95},
            "rework_per_task": {"baseline": 2.0, "skein": 1.0},
            "handoff_loss_rate": {"baseline": 0.20, "skein": 0.05},
        }
    }))
    result = run_intelligence(tmp_path)
    assert result["scorecard"]["provider_token_reduction"]["value_pct"] == 40.0
    assert result["scorecard"]["llm_cost_reduction"]["value_pct"] == 40.0
    assert result["scorecard"]["task_success"]["value"] == 0.95
    assert result["evidence_quality"]["production_quality_claim_allowed"] is True
    assert result["targets"]["checks"]["success_target"] is True
    assert "Pilot Intelligence Report" in render_report(result)
