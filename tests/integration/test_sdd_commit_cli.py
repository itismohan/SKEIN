from pathlib import Path
from typer.testing import CliRunner
from skein.cli import app

ROOT = Path(__file__).parents[2]


def test_commit_graph_cli_creates_trace(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "spec" / "clauses").mkdir(parents=True)
    for source in (ROOT / "spec" / "clauses").glob("*.yaml"):
        (workspace / "spec" / "clauses" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["init", str(workspace)]).exit_code == 0
    result = runner.invoke(app, ["commit-graph", str(workspace), "--spec", "SKN-001", "--author", "agent:coder"])
    assert result.exit_code == 0, result.stdout
    trace = runner.invoke(app, ["trace", "--spec", "SKN-001", str(workspace)])
    assert trace.exit_code == 0
    assert "IMPLEMENTED_BY" in trace.stdout
