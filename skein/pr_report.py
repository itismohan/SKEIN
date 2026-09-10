"""CI-friendly structural diff report generation."""
from __future__ import annotations
from .versioning import VersionedGraphStore, diff_graphs

def markdown_report(store: VersionedGraphStore, base: str, head: str | None = None) -> str:
    before = store.state_at(base)
    after = store.graph if head is None else store.state_at(head)
    delta = diff_graphs(before, after)
    changed_nodes = []
    for item in delta["nodes"]["added"]:
        changed_nodes.append((item["id"], "added"))
    for item in delta["nodes"]["removed"]:
        changed_nodes.append((item["id"], "removed"))
    for item in delta["nodes"]["modified"]:
        changed_nodes.append((item["id"], "modified"))
    lines = ["# Skein Structural Diff", "", f"Base: `{base}`", f"Head: `{head or store.head}`", "", "## Summary", "",
             f"- Nodes added: **{len(delta['nodes']['added'])}**", f"- Nodes removed: **{len(delta['nodes']['removed'])}**",
             f"- Nodes modified: **{len(delta['nodes']['modified'])}**", f"- Edges added: **{len(delta['edges']['added'])}**",
             f"- Edges removed: **{len(delta['edges']['removed'])}**", f"- Edges modified: **{len(delta['edges']['modified'])}**",
             f"- Confidence changes: **{len(delta['confidence_changes'])}**", "", "## Changed Functions / Graph Elements", ""]
    for node_id, action in sorted(changed_nodes):
        lines.append(f"- `{node_id}` — {action}")
    if not changed_nodes:
        lines.append("- No node changes")
    lines += ["", "## Confidence Changes", ""]
    if delta["confidence_changes"]:
        for item in delta["confidence_changes"]:
            lines.append(f"- `{item['source']}` → `{item['target']}`: `{item['before']}` → `{item['after']}`")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"
