from __future__ import annotations
from pathlib import Path
from .base import AgentRun, ReferenceAgentClient

class FrameworkBClient(ReferenceAgentClient):
    """Second adapter with message-oriented sequencing semantics."""
    framework = "framework-b"

    def execute(self, messages: list[tuple[str, dict]]) -> list[dict]:
        results = []
        for tool, payload in messages:
            results.append(self.call(tool, **payload))
        return results


def run_pipeline(root: Path) -> AgentRun:
    client = FrameworkBClient(root, "local-admin")
    results = client.execute([
        ("query_graph", {"query":"what calls create_order"}),
        ("propose_node", {"node":{"id":"b:plan:1","kind":"Plan","attributes":{"framework":"b"}}}),
    ])
    from ..server import _proposals
    pid = _proposals(root)[-1]["proposal_id"]
    client.call("commit_proposal", proposal_id=pid, spec_refs=["SKN-007"])
    return AgentRun(framework=FrameworkBClient.framework, calls=client.calls, proposal_id=pid, commit_id=_proposals(root)[-1]["commit_id"])
