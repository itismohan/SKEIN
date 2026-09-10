import json
from pathlib import Path
from skein.experiment import *


def test_deterministic_assignment(tmp_path: Path):
    save_config(tmp_path, ExperimentConfig(seed=7, repository_commit="abc", model="m", provider="p", prompt_hash="ph", graph_head="gh"))
    add_tasks(tmp_path, [TaskSpec(f"T{i}", f"task {i}") for i in range(10)])
    a1 = assign_tasks(tmp_path); a2 = assign_tasks(tmp_path)
    assert a1 == a2
    assert {a.arm for a in a1} == {"baseline", "skein"}


def test_manifest_verification_and_tamper(tmp_path: Path):
    cfg=ExperimentConfig(repository_commit="abc", model="m", provider="p", prompt_hash="ph", graph_head="gh")
    save_config(tmp_path,cfg); add_tasks(tmp_path,[TaskSpec("T1","one"),TaskSpec("T2","two")])
    m=create_manifest(tmp_path,assign_tasks(tmp_path,cfg)); assert verify_manifest(m)
    m["config"]["seed"]=999
    assert not verify_manifest(m)


def test_confounds_are_explicit(tmp_path: Path):
    cfg=ExperimentConfig(repository_commit="unknown")
    save_config(tmp_path,cfg); add_tasks(tmp_path,[TaskSpec("T1","one")])
    m=create_manifest(tmp_path,assign_tasks(tmp_path,cfg))
    assert any(x["type"] == "repository" for x in m["confounds"])
    assert any(x["type"] == "model" for x in m["confounds"])


def test_power_guidance():
    p=power_guidance(10,2)
    assert p["approx_pairs"] > 0
    assert p["design"] == "paired-continuous-approximation"
