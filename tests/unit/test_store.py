from pathlib import Path

from skein.schema import EdgeType, GraphEdge, GraphNode, NodeType
from skein.store import LocalGraphStore


def test_local_store_round_trip(tmp_path: Path) -> None:
    store = LocalGraphStore()
    store.add_node(GraphNode(id="file:app.py", type=NodeType.FILE, attributes={"path": "app.py"}))
    store.add_node(GraphNode(id="fn:calculate_total", type=NodeType.FUNCTION, attributes={"name": "calculate_total"}))
    store.add_edge(GraphEdge(source="file:app.py", target="fn:calculate_total", type=EdgeType.EXTRACTED))

    path = tmp_path / "graph.json"
    store.save(path)
    loaded = LocalGraphStore.load(path)

    assert loaded.get_node("fn:calculate_total") is not None
    assert loaded.graph.number_of_nodes() == 2
    assert loaded.graph.number_of_edges() == 1
