from skein.mcp.benchmark import measure_duplicate_context

def test_shared_graph_reduces_duplicate_context_calls():
    r=measure_duplicate_context(3)
    assert r['baseline_context_calls']==3
    assert r['shared_graph_context_calls']==1
    assert r['reduction_pct'] > 50
