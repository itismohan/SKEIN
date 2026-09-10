from pathlib import Path
import json
import pytest
from skein.control_plane import ControlPlane, ControlTask


def test_control_plane_full_governed_lifecycle(tmp_path: Path):
    cp = ControlPlane(tmp_path)
    (tmp_path / ".skein").mkdir(exist_ok=True)
    (tmp_path / ".skein" / "policy.json").write_text(json.dumps({"identities": {"local-admin": "admin", "reviewer-1": "reviewer"}}))
    run = cp.create(ControlTask("T1", "Add feature", "Implement feature", ("SKN-001",), "high", True))
    assert run.state == "created"
    assert cp.plan().state == "planned"
    assert cp.begin_execution(selection_id="sel-1").state == "executing"
    evaluated = cp.record_evaluation(passed=True, score=0.95, execution_id="exec-1")
    assert evaluated.state == "approval_required"
    approved = cp.approve(actor="reviewer-1", reason="Quality evidence reviewed")
    assert approved.state == "approved"
    assert cp.finalize().state == "completed"
    exported = cp.export()
    assert exported["run"]["state"] == "completed"
    assert exported["integrity"]
    assert len(exported["events"]) >= 5


def test_control_plane_rejects_invalid_transition(tmp_path: Path):
    cp = ControlPlane(tmp_path)
    cp.create(ControlTask("T1", "x", "x"))
    with pytest.raises(ValueError):
        cp.finalize()


def test_failed_quality_is_terminal(tmp_path: Path):
    cp = ControlPlane(tmp_path)
    cp.create(ControlTask("T1", "x", "x", required_approval=False))
    cp.plan(); cp.begin_execution()
    run = cp.record_evaluation(passed=False, score=0.2)
    assert run.state == "failed"
    assert cp.status()["terminal"] is True


def test_critical_approval_can_be_explicitly_recorded(tmp_path: Path):
    cp = ControlPlane(tmp_path)
    cp.create(ControlTask("T2", "critical", "critical change", risk="critical", required_approval=True))
    assert cp.plan().task.risk == "critical"


def test_control_export_is_json_serializable(tmp_path: Path):
    cp = ControlPlane(tmp_path)
    cp.create(ControlTask("T1", "x", "x"))
    json.dumps(cp.export())
