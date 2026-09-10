from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .store import LocalGraphStore


def raw_context(root: Path, question: str) -> str:
    """Baseline: give the agent every supported repository text file."""
    chunks: list[str] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".skein" not in p.parts and p.suffix.lower() in {
            ".py", ".js", ".ts", ".md", ".txt", ".rst"
        }:
            chunks.append(f"# FILE: {p.relative_to(root).as_posix()}\n{p.read_text(errors='ignore')}")
    return "\n\n".join(chunks)


def graph_context(store: LocalGraphStore, question: str) -> str:
    """Structural retrieval for the current Stage 1 question family."""
    target = re.search(r"calls ([\w.:-]+)", question, re.I)
    if not target:
        return json.dumps(store.to_document().to_contract(), separators=(",", ":"))
    needle = target.group(1).strip('"\'')
    matches = [
        n
        for n, d in store.graph.nodes(data=True)
        if needle in n
        or needle == d.get("attributes", {}).get("name")
        or needle == d.get("attributes", {}).get("qualified_name")
    ]
    lines = [f"QUESTION TARGET: {needle}"]
    for target_node in matches:
        data = store.graph.nodes[target_node]
        lines.append(f"TARGET {target_node} {data.get('attributes', {})}")
        for caller, _, edge_data in store.graph.in_edges(target_node, data=True):
            if edge_data.get("type") == "CALLS":
                lines.append(
                    f"CALLER {caller} confidence={edge_data.get('attributes', {}).get('confidence', 'UNKNOWN')}"
                )
    return "\n".join(lines)


def tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    question: str
    expected_callers: tuple[str, ...]


CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        "Q01",
        "what calls create_order?",
        ("post_order", "_process"),
    ),
    BenchmarkCase(
        "Q02",
        "what calls pay_order?",
        ("post_payment",),
    ),
    BenchmarkCase(
        "Q03",
        "what calls authorize_payment?",
        ("post_authorization", "pay_order"),
    ),
    BenchmarkCase(
        "Q04",
        "what calls cancel_order?",
        ("delete_order", "process_order_cancelled"),
    ),
    BenchmarkCase(
        "Q05",
        "what calls get_order?",
        ("get_order_status",),
    ),
    BenchmarkCase(
        "Q06",
        "what calls health_check?",
        ("readiness_check",),
    ),
)


def _function_names(text: str) -> set[str]:
    return set(re.findall(r"(?:def|async def|function)\s+([A-Za-z_$][\w$]*)", text))


def _graph_function_names(context: str) -> set[str]:
    names = set()
    for line in context.splitlines():
        if not line.startswith("CALLER "):
            continue
        m = re.search(r"function:.*:([A-Za-z_$][\w$]*)\s+confidence=", line)
        if m:
            names.add(m.group(1))
    return names


def _metrics(context: str, expected: tuple[str, ...], *, graph: bool) -> dict[str, Any]:
    expected_set = set(expected)
    present = _graph_function_names(context) if graph else _function_names(context)
    true_positive = len(present & expected_set)
    precision = true_positive / len(present) if present else 0.0
    recall = true_positive / len(expected_set) if expected_set else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "relevant_functions": sorted(present),
        "true_positive": true_positive,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def run_suite(root: Path) -> dict[str, Any]:
    store = LocalGraphStore.load(root / ".skein" / "graph.json")
    results = []
    for case in CASES:
        raw = raw_context(root, case.question)
        graph = graph_context(store, case.question)
        raw_tokens, graph_tokens = tokens(raw), tokens(graph)
        reduction = (1 - graph_tokens / raw_tokens) * 100 if raw_tokens else 0.0
        results.append(
            {
                "id": case.id,
                "question": case.question,
                "expected_callers": list(case.expected_callers),
                "raw_tokens": raw_tokens,
                "graph_tokens": graph_tokens,
                "token_reduction_pct": round(reduction, 2),
                "raw": _metrics(raw, case.expected_callers, graph=False),
                "graph": _metrics(graph, case.expected_callers, graph=True),
            }
        )
    return {
        "benchmark": "skein-stage-1-structural-retrieval",
        "fixture": root.name,
        "cases": results,
        "summary": {
            "cases": len(results),
            "avg_raw_tokens": round(sum(r["raw_tokens"] for r in results) / len(results), 2),
            "avg_graph_tokens": round(sum(r["graph_tokens"] for r in results) / len(results), 2),
            "avg_token_reduction_pct": round(
                sum(r["token_reduction_pct"] for r in results) / len(results), 2
            ),
            "avg_raw_precision": round(sum(r["raw"]["precision"] for r in results) / len(results), 4),
            "avg_graph_precision": round(sum(r["graph"]["precision"] for r in results) / len(results), 4),
            "avg_raw_recall": round(sum(r["raw"]["recall"] for r in results) / len(results), 4),
            "avg_graph_recall": round(sum(r["graph"]["recall"] for r in results) / len(results), 4),
            "avg_raw_f1": round(sum(r["raw"]["f1"] for r in results) / len(results), 4),
            "avg_graph_f1": round(sum(r["graph"]["f1"] for r in results) / len(results), 4),
        },
    }
