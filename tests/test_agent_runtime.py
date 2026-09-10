import json
from pathlib import Path

from skein.agent_runtime import ExecutionRequest, execute, execution_summary
from skein.experiment import ExperimentConfig, TaskSpec, add_tasks, assign_tasks, create_manifest, save_config, write_manifest


def setup_experiment(root: Path, arm="baseline"):
    save_config(root, ExperimentConfig(seed=11, repository_commit="abc", model="m", provider="p", prompt_hash="ph", graph_head="gh"))
    add_tasks(root, [TaskSpec("T1", "what calls checkout?")])
    write_manifest(root, create_manifest(root, assign_tasks(root)))
    manifest=json.loads((root/".skein"/"experiment-results.json").read_text())
    return manifest["assignments"][0]["arm"]


def test_controlled_argv_execution_and_telemetry(tmp_path: Path):
    arm=setup_experiment(tmp_path)
    record=execute(tmp_path, ExecutionRequest("T1", arm, ("python", "-c", "print('ok')")))
    assert record.outcome == "success"
    assert record.exit_code == 0
    assert record.execution_id
    assert (tmp_path/".skein/history/agent-executions.jsonl").exists()
    events=(tmp_path/".skein/history/connector-events.jsonl").read_text()
    assert "agent_execution" in events


def test_failed_agent_is_recorded(tmp_path: Path):
    arm=setup_experiment(tmp_path)
    record=execute(tmp_path, ExecutionRequest("T1", arm, ("python", "-c", "raise SystemExit(3)")))
    assert record.outcome == "failure"
    assert record.exit_code == 3
    assert execution_summary(tmp_path)["successes"] == 0


def test_assignment_gate_blocks_unassigned_arm(tmp_path: Path):
    setup_experiment(tmp_path)
    try:
        execute(tmp_path, ExecutionRequest("T1", "invalid", ("python", "-c", "print(1)")))
    except ValueError as exc:
        assert "no assignment for arm" in str(exc)
    else:
        raise AssertionError("unassigned arm was executed")
