"""Verification telemetry for the compression layer."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json


class CompressionTelemetry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = root / "compression_verification.jsonl"

    def record(self, *, outcome: str, original_tokens: int, compressed_tokens: int,
               checklist_items: int, metadata: dict[str, object] | None = None) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "checklist_items": checklist_items,
            "tokens_saved": max(0, original_tokens - compressed_tokens),
            "metadata": metadata or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def health(self) -> dict[str, object]:
        rows = self.records()
        counts = {k: sum(1 for r in rows if r["outcome"] == k) for k in ("pass", "fallback", "re_expand")}
        total = len(rows)
        return {
            "total": total,
            **counts,
            "pass_rate": counts["pass"] / total if total else 0.0,
            "fallback_rate": counts["fallback"] / total if total else 0.0,
            "re_expand_rate": counts["re_expand"] / total if total else 0.0,
            "avg_tokens_saved": sum(r.get("tokens_saved", 0) for r in rows) / total if total else 0.0,
        }
