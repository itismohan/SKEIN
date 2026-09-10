from pathlib import Path
from skein.mcp.certification import run_certification


def test_mcp_certification(tmp_path):
    report = run_certification(Path("."))
    assert report["passed"]
    assert report["checks"]["framework_a_pipeline"]
    assert report["checks"]["framework_b_pipeline"]
    assert report["checks"]["shared_context_reduction"]
