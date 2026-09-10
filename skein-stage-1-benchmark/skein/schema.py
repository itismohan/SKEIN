"""Versioned graph contract and validation."""
from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "graph.schema.json"


class NodeType(StrEnum):
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    REQUIREMENT = "Requirement"
    TICKET = "Ticket"
    ADR = "ADR"
    TEST_CASE = "TestCase"


class EdgeType(StrEnum):
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    JUSTIFIES = "JUSTIFIES"
    TESTS = "TESTS"
    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    type: NodeType
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    type: EdgeType
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    def to_contract(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def validate_graph(document: GraphDocument | dict[str, Any]) -> None:
    """Validate through both Pydantic and the external JSON Schema contract."""
    graph = document if isinstance(document, GraphDocument) else GraphDocument.model_validate(document)
    if graph.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported graph schema version: {graph.schema_version}")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(graph.to_contract()), key=lambda e: list(e.path))
    if errors:
        raise ValueError("Graph schema validation failed: " + "; ".join(e.message for e in errors))
