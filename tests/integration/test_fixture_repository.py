from pathlib import Path

from skein.schema import EdgeType, GraphEdge, GraphNode, NodeType
from skein.store import LocalGraphStore

FIXTURE = Path(__file__).parents[1] / "fixtures" / "tiny_repo"


def test_tiny_fixture_graph_shape() -> None:
    store = LocalGraphStore()
    store.add_node(GraphNode(id="file:app.py", type=NodeType.FILE, attributes={"path": str(FIXTURE / "app.py")}))
    store.add_node(GraphNode(id="fn:calculate_total", type=NodeType.FUNCTION, attributes={"name": "calculate_total"}))
    store.add_node(GraphNode(id="test:test_calculate_total", type=NodeType.TEST_CASE, attributes={"name": "test_calculate_total"}))
    store.add_edge(GraphEdge(source="file:app.py", target="fn:calculate_total", type=EdgeType.EXTRACTED))
    store.add_edge(GraphEdge(source="test:test_calculate_total", target="fn:calculate_total", type=EdgeType.TESTS))

    document = store.to_document()
    assert {node.type.value for node in document.nodes} == {"File", "Function", "TestCase"}
    assert {edge.type.value for edge in document.edges} == {"EXTRACTED", "TESTS"}
