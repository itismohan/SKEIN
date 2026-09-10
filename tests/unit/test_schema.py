from skein.schema import GraphDocument, validate_graph


def test_empty_graph_matches_v1_contract() -> None:
    graph = GraphDocument()
    validate_graph(graph)
    assert graph.schema_version == "1.0.0"
