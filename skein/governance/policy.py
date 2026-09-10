"""Identity-based authorization policy for dashboard and MCP operations."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

DEFAULT_ROLES = {
    "planner": {"read_graph", "read_trace", "propose"},
    "coder": {"read_graph", "read_trace", "propose"},
    "tester": {"read_graph", "read_trace", "propose"},
    "reviewer": {"read_graph", "read_trace", "propose", "commit"},
    "auditor": {"read_graph", "read_trace", "read_cost", "export_audit"},
    "admin": {"read_graph", "read_trace", "read_cost", "export_audit", "propose", "commit"},
}

@dataclass(frozen=True)
class IdentityPolicy:
    identities: dict[str, str]
    roles: dict[str, set[str]]

    def role_for(self, identity: str) -> str:
        if identity not in self.identities:
            raise PermissionError(f"unknown identity: {identity}")
        return self.identities[identity]

    def allowed(self, identity: str, action: str) -> bool:
        role = self.role_for(identity)
        return action in self.roles.get(role, set())


def load_policy(path: Path) -> IdentityPolicy:
    if not path.exists():
        return IdentityPolicy({"local-admin": "admin"}, {k: set(v) for k, v in DEFAULT_ROLES.items()})
    data = json.loads(path.read_text(encoding="utf-8"))
    roles = {k: set(v) for k, v in data.get("roles", DEFAULT_ROLES).items()}
    return IdentityPolicy(dict(data.get("identities", {"local-admin": "admin"})), roles)
