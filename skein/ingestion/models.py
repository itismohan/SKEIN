from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass(frozen=True)
class ParsedNode:
    id: str
    type: str
    attributes: dict = field(default_factory=dict)

@dataclass(frozen=True)
class ParsedEdge:
    source: str
    target: str
    type: str
    confidence: Literal["EXTRACTED", "INFERRED"]
    attributes: dict = field(default_factory=dict)

@dataclass
class ParseResult:
    nodes: list[ParsedNode] = field(default_factory=list)
    edges: list[ParsedEdge] = field(default_factory=list)

@dataclass(frozen=True)
class SourceFile:
    path: Path
    content_hash: str
    language: str
