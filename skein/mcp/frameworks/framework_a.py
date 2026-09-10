from __future__ import annotations
from pathlib import Path
from .base import AgentRun, ReferenceAgentClient

class FrameworkAClient(ReferenceAgentClient):
    """Planner/coder/reviewer adapter using direct tool invocation."""
    framework = "framework-a"


def run_pipeline(root: Path) -> AgentRun:
    planner = FrameworkAClient(root, "local-admin")
    planner.call("propose_node", node={"id":"a:plan:1","kind":"Plan","attributes":{"framework":"a"}})
    # Admin is used only by this offline harness; production policy should map distinct identities.
    proposal = planner.calls[-1]
    reviewer = FrameworkAClient(root, "local-admin")
    # Locate the deterministic proposal created by the planner.
    from ..server import _proposals
    proposals = _proposals(root)
    pid = proposals[-1]["proposal_id"]
    reviewer.call("get_traceability", spec_ref="SKN-007")
    result = reviewer.call("commit_proposal", proposal_id=pid, spec_refs=["SKN-007"])
    return AgentRun(framework=FrameworkAClient.framework, calls=planner.calls + reviewer.calls, proposal_id=pid, commit_id=result["commit_id"])
