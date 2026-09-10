"""Post-write graph sanity checks."""
from __future__ import annotations
from dataclasses import dataclass, field
import networkx as nx
from .schema import GraphDocument, validate_graph

@dataclass
class SanityReport:
    valid: bool
    errors: list[str] = field(default_factory=list)

def check_graph(graph: GraphDocument) -> SanityReport:
    errors: list[str] = []
    try:
        validate_graph(graph)
    except Exception as exc:
        errors.append(f"schema: {exc}")
    ids = {n.id for n in graph.nodes}
    for edge in graph.edges:
        if edge.source not in ids:
            errors.append(f"orphan edge source: {edge.source}")
        if edge.target not in ids:
            errors.append(f"orphan edge target: {edge.target}")
    g = nx.Graph()
    g.add_nodes_from(ids)
    g.add_edges_from((e.source, e.target) for e in graph.edges if e.source in ids and e.target in ids)
    # Community sanity: every node belongs to exactly one detected community.
    if g.number_of_nodes():
        communities = list(nx.community.greedy_modularity_communities(g)) if g.number_of_edges() else [{n} for n in g.nodes]
        flattened = [n for c in communities for n in c]
        if len(flattened) != len(set(flattened)) or set(flattened) != ids:
            errors.append("community detection integrity check failed")
    return SanityReport(not errors, errors)
