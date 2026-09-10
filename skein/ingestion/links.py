from __future__ import annotations
import re
from pathlib import Path
from .models import ParsedEdge

ID_RE = re.compile(r"\b(?:[A-Z]{2,10}-\d+|ADR[-_ ]?\d+)\b", re.I)

def ticket_adr_links(path: Path, text: str, known_nodes: set[str]) -> list[ParsedEdge]:
    edges=[]
    refs={m.group(0).upper().replace(" ", "-") for m in ID_RE.finditer(text)}
    for ref in refs:
        target = next((nid for nid in known_nodes if nid.endswith(f":{ref}") or nid.endswith(f"/{ref}")), f"reference:{ref}")
        edges.append(ParsedEdge(f"file:{path.as_posix()}", target, "JUSTIFIES", "INFERRED", {"reference": ref, "heuristic": "id-match"}))
    return edges
