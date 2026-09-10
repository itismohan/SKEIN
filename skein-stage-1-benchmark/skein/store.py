"""Storage abstraction and local NetworkX implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable
import json

import networkx as nx

from .schema import GraphDocument, GraphEdge, GraphNode, validate_graph


class GraphStore(ABC):
    """Storage-agnostic contract for later graph database adapters."""

    @abstractmethod
    def add_node(self, node: GraphNode) -> None: ...

    @abstractmethod
    def add_edge(self, edge: GraphEdge) -> None: ...

    @abstractmethod
    def get_node(self, node_id: str) -> GraphNode | None: ...

    @abstractmethod
    def to_document(self) -> GraphDocument: ...

    @abstractmethod
    def save(self, path: Path) -> None: ...


class LocalGraphStore(GraphStore):
    """Local-first property graph backed by NetworkX."""

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_node(self, node: GraphNode) -> None:
        self.graph.add_node(node.id, type=node.type.value, attributes=node.attributes)

    def add_edge(self, edge: GraphEdge) -> None:
        if not self.graph.has_node(edge.source) or not self.graph.has_node(edge.target):
            raise ValueError("Both edge endpoints must exist before an edge is added")
        self.graph.add_edge(
            edge.source, edge.target, type=edge.type.value, attributes=edge.attributes
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        if node_id not in self.graph:
            return None
        data = self.graph.nodes[node_id]
        return GraphNode(id=node_id, type=data["type"], attributes=data.get("attributes", {}))

    def to_document(self) -> GraphDocument:
        nodes = [
            GraphNode(id=node_id, type=data["type"], attributes=data.get("attributes", {}))
            for node_id, data in self.graph.nodes(data=True)
        ]
        edges = [
            GraphEdge(
                source=source,
                target=target,
                type=data["type"],
                attributes=data.get("attributes", {}),
            )
            for source, target, data in self.graph.edges(data=True)
        ]
        document = GraphDocument(nodes=nodes, edges=edges)
        validate_graph(document)
        return document

    def save(self, path: Path) -> None:
        document = self.to_document()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document.to_contract(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "LocalGraphStore":
        data = json.loads(path.read_text(encoding="utf-8"))
        document = GraphDocument.model_validate(data)
        validate_graph(document)
        store = cls()
        for node in document.nodes:
            store.add_node(node)
        for edge in document.edges:
            store.add_edge(edge)
        return store
