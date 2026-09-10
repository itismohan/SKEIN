from __future__ import annotations
import re
from pathlib import Path
from .models import ParseResult, ParsedNode, ParsedEdge

class DocumentExtractor:
    """Provider interface boundary for LLM extraction. Offline mode emits conservative candidates."""
    def extract(self, path: Path, text: str) -> ParseResult:
        result = ParseResult()
        suffix = path.suffix.lower()
        if suffix == ".pdf" and not text:
            try:
                from pypdf import PdfReader
                text = "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
            except ImportError:
                pass
        node_type = "ADR" if "adr" in path.name.lower() else "Ticket" if any(x in path.name.lower() for x in ("ticket", "issue")) else "Requirement"
        nid = f"document:{path.as_posix()}"
        result.nodes.append(ParsedNode(nid, node_type, {"path": path.as_posix(), "title": path.stem, "source": "document"}))
        for match in re.finditer(r"\b(?:[A-Z]{2,10}-\d+|ADR[-_ ]?\d+)\b", text, re.I):
            ref = match.group(0).upper().replace(" ", "-")
            result.edges.append(ParsedEdge(nid, f"reference:{ref}", "INFERRED", "INFERRED", {"reference": ref, "source": "document-text"}))
        return result
