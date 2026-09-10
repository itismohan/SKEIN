import json
from pathlib import Path
from skein.evaluation import EvaluationConfig, evaluate, render_report


def test_evaluation_requires_pairs(tmp_path: Path):
    (tmp_path / ".skein").mkdir()
    result = evaluate(tmp_path)
    assert result["paired_tasks"] == 0
    assert result["claim_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["evidence_grade"] == "D"


def test_evaluation_bootstrap_supports_clear_improvement(tmp_path: Path):
    d = tmp_path / ".skein"; d.mkdir()
    rows=[]
    for i in range(12):
        rows += [
            {"task_id":f"T{i}","experiment":"baseline","input_tokens":1000,"cost_usd":0.10,"latency_ms":1000,"rework_count":2,"handoff_loss_rate":0.2,"success":True},
            {"task_id":f"T{i}","experiment":"skein","input_tokens":600,"cost_usd":0.06,"latency_ms":700,"rework_count":1,"handoff_loss_rate":0.1,"success":True},
        ]
    (d/"pilot-task-results.json").write_text(json.dumps({"tasks":rows}))
    result=evaluate(tmp_path, EvaluationConfig(bootstrap_samples=500, minimum_tasks=10))
    assert result["paired_tasks"] == 12
    assert result["metrics"]["context_tokens"]["improvement_pct"] == 40.0
    assert result["metrics"]["cost_usd"]["statistically_supported"]
    assert result["success"]["guardrail_pass"]
    assert result["claim_status"] == "SUPPORTED"
    assert "Skein v0.5 Evaluation Report" in render_report(result)
