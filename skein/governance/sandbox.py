"""Conservative ingestion/MCP sandbox boundary for the MVP."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

class SandboxViolation(PermissionError):
    pass

@dataclass(frozen=True)
class SandboxPolicy:
    root: Path
    max_file_bytes: int = 5_000_000
    allow_subprocess: bool = False
    allow_network: bool = False

    def check_path(self, path: Path) -> Path:
        root = self.root.resolve()
        candidate = path.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise SandboxViolation(f"path escapes sandbox root: {candidate}") from exc
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > self.max_file_bytes:
            raise SandboxViolation(f"file exceeds sandbox size limit: {candidate}")
        return candidate

    def check_execution(self, *, subprocess: bool = False, network: bool = False) -> None:
        if subprocess and not self.allow_subprocess:
            raise SandboxViolation("subprocess execution is disabled by Skein sandbox policy")
        if network and not self.allow_network:
            raise SandboxViolation("network execution is disabled by Skein sandbox policy")
