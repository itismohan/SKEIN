from pathlib import Path

from skein.benchmarks import run_suite
from skein.ingestion.pipeline import IncrementalIngester
from skein.store import LocalGraphStore


FIXTURE = Path(__file__).parents[2] / "benchmarks" / "fixtures" / "commerce_service"


def test_stage1_benchmark_has_measurable_reduction_and_retrieval_quality():
    store = LocalGraphStore()
    IncrementalIngester(FIXTURE, store).ingest(full_rebuild=True)
    # The benchmark expects the fixture's persisted graph under .skein.
    fixture_store = LocalGraphStore()
    IncrementalIngester(FIXTURE, fixture_store).ingest(full_rebuild=True)
    fixture_store.save(FIXTURE / ".skein" / "graph.json")

    result = run_suite(FIXTURE)
    assert result["summary"]["avg_token_reduction_pct"] > 90
    assert result["summary"]["avg_graph_precision"] >= 0.95
    assert result["summary"]["avg_graph_recall"] >= 0.9
