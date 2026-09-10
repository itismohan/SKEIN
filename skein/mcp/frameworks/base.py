from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ..server import call_tool

@dataclass
class AgentRun:
    framework: str
    calls: list[str]
    proposal_id: str | None = None
    commit_id: str | None = None

class ReferenceAgentClient:
    framework = "reference"

    def __init__(self, root: Path, identity: str):
        self.root = root
        self.identity = identity
        self.calls: list[str] = []

    def call(self, tool: str, **arguments: Any) -> dict[str, Any]:
        self.calls.append(tool)
        arguments["identity"] = self.identity
        return call_tool(tool, arguments, self.root)
