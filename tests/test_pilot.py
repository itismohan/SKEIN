from pathlib import Path

from skein.pilot import init_pilot, load_config, render_report, run_pilot


def make_workspace(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "app.py").write_text(
        "def main():\n    return helper()\n\ndef helper():\n    return 42\n", encoding="utf-8"
    )
    (root / "spec" / "clauses").mkdir(parents=True)
    repo = Path(__file__).resolve().parents[1]
    for p in (repo / "spec" / "clauses").glob("*.yaml"):
        (root / "spec" / "clauses" / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    return root


def test_pilot_config_round_trip(tmp_path: Path):
    target = init_pilot(tmp_path, name="partner-a", agents=4)
    assert target.exists()
    cfg = load_config(tmp_path)
    assert cfg.name == "partner-a"
    assert cfg.agents == 4


def test_pilot_run_is_deterministic_shape(tmp_path: Path):
    root = make_workspace(tmp_path)
    (root / ".skein").mkdir()
    from skein.ingestion.pipeline import IncrementalIngester
    from skein.store import LocalGraphStore
    store = LocalGraphStore()
    IncrementalIngester(root, store).ingest(full_rebuild=True)
    store.save(root / ".skein" / "graph.json")
    init_pilot(root)
    result = run_pilot(root)
    assert result["retrieval"]["cases"] == 6
    assert result["context_efficiency"]["baseline_tokens"] > result["context_efficiency"]["skein_tokens"]
    assert 0 <= result["retrieval"]["f1"] <= 1
    report = render_report(result)
    assert "Skein Pilot Report" in report
    assert "Limitations" in report


def test_scenario_template_and_runner(tmp_path: Path):
    from skein.pilot import init_scenario_pilot, run_scenario_pilot, render_scenario_report
    target = init_scenario_pilot(tmp_path, name="partner-a")
    data = __import__("json").loads(target.read_text(encoding="utf-8"))
    data["scenarios"][0]["baseline"] = ["python", "-c", "print('baseline')"]
    data["scenarios"][0]["skein"] = ["python", "-c", "print('skein')"]
    target.write_text(__import__("json").dumps(data), encoding="utf-8")
    result = run_scenario_pilot(tmp_path)
    assert len(result["results"]) == 2
    assert all(r["exit_code"] == 0 for r in result["results"])
    report = render_scenario_report(result)
    assert "baseline" in report and "skein" in report
