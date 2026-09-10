from pathlib import Path
import json

from skein.context_intelligence import AdaptiveContextEngine
from skein.schema import GraphEdge, GraphNode
from skein.store import LocalGraphStore


def make_root(tmp_path: Path) -> Path:
    root = tmp_path
    (root / ".skein").mkdir()
    store = LocalGraphStore()
    for node in [
        GraphNode(id="file:orders.py", type="File", attributes={"name":"orders.py","path":"orders.py"}),
        GraphNode(id="function:create_order", type="Function", attributes={"name":"create_order","qualified_name":"orders.create_order","text":"create order validate payment"}),
        GraphNode(id="function:refund", type="Function", attributes={"name":"refund","qualified_name":"orders.refund","text":"refund payment order"}),
        GraphNode(id="function:health", type="Function", attributes={"name":"health","qualified_name":"health.health","text":"health check"}),
    ]:
        store.add_node(node)
    store.add_edge(GraphEdge(source="file:orders.py", target="function:create_order", type="EXTRACTED", attributes={}))
    store.add_edge(GraphEdge(source="file:orders.py", target="function:refund", type="EXTRACTED", attributes={}))
    store.save(root / ".skein" / "graph.json")
    return root


def test_selection_is_budgeted_and_relevant(tmp_path):
    root = make_root(tmp_path)
    result = AdaptiveContextEngine(root, budget_tokens=20).select("T1", "create order payment")
    assert result.total_tokens <= 20
    assert result.selected
    assert result.selected[0].node_id == "function:create_order"
    assert result.strategy == "adaptive-v1"


def test_feedback_changes_ranking(tmp_path):
    root = make_root(tmp_path)
    engine = AdaptiveContextEngine(root)
    first = engine.select("T1", "payment order", budget_tokens=30)
    target = next(c for c in first.selected if c.node_id == "function:refund")
    engine.feedback_event(first.selection_id, target.node_id, -1.0, task_id="T1", reason="irrelevant")
    second = engine.select("T2", "payment order", budget_tokens=30)
    ranked = {c.node_id: c.score for c in second.selected}
    assert ranked[target.node_id] < target.score


def test_feedback_is_bounded(tmp_path):
    root = make_root(tmp_path)
    engine = AdaptiveContextEngine(root)
    event = engine.feedback_event("s", "function:refund", 1.0)
    assert event.reward == 1.0
    assert engine.feedback.scores()["function:refund"] == 1.0


def test_quality_loop_retries_and_learns(tmp_path):
    from skein.autonomous_loop import QualitySignal, run_quality_loop
    from skein.agent_adapters import CallableAdapter
    from skein.store import LocalGraphStore
    from skein.schema import GraphNode, GraphEdge

    skein = tmp_path / ".skein"
    skein.mkdir()
    store = LocalGraphStore()
    store.add_node(GraphNode(id="File:checkout.py", type="File", attributes={"name": "checkout.py", "path": "checkout.py", "text": "checkout payment"}))
    store.add_node(GraphNode(id="Function:charge", type="Function", attributes={"name": "charge", "qualified_name": "charge", "text": "charge payment"}))
    store.add_edge(GraphEdge(source="File:checkout.py", target="Function:charge", type="CALLS"))
    store.save(skein / "graph.json")

    calls = {"n": 0}
    def invoke(request):
        calls["n"] += 1
        return {"outcome": "failure" if calls["n"] == 1 else "success", "response": "ok", "input_tokens": 10, "output_tokens": 2}
    adapter = CallableAdapter(invoke)

    def evaluate(request, result):
        return QualitySignal(passed=result.outcome == "success", score=1.0 if result.outcome == "success" else 0.0, reason="test gate")

    result = run_quality_loop(tmp_path, task_id="T1", task_description="checkout payment", adapter=adapter, max_iterations=2, evaluator=evaluate)
    assert result.passed is True
    assert len(result.iterations) == 2
    assert calls["n"] == 2
    assert (tmp_path / ".skein/history/quality-loops.jsonl").exists()
    assert (tmp_path / ".skein/history/context-feedback.jsonl").exists()


def test_quality_loop_respects_non_retryable(tmp_path):
    from skein.autonomous_loop import QualitySignal, run_quality_loop
    from skein.agent_adapters import CallableAdapter
    from skein.store import LocalGraphStore
    from skein.schema import GraphNode

    skein = tmp_path / ".skein"
    skein.mkdir()
    store = LocalGraphStore()
    store.add_node(GraphNode(id="Requirement:R1", type="Requirement", attributes={"name": "payment", "text": "payment requirement"}))
    store.save(skein / "graph.json")
    adapter = CallableAdapter(lambda request: {"outcome": "failure"})
    evaluator = lambda request, result: QualitySignal(False, 0.0, "blocked", retryable=False)
    result = run_quality_loop(tmp_path, task_id="T2", task_description="payment", adapter=adapter, max_iterations=5, evaluator=evaluator)
    assert result.passed is False
    assert len(result.iterations) == 1
    assert result.stop_reason == "quality_gate_non_retryable"
