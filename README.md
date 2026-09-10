# Skein

<p align="center">
  <img src="assets/skein-logo.png" alt="Skein — The Continuous Thread of AI-DLC" width="760">
</p>

<p align="center">
  <strong>The Continuous Thread of AI-DLC</strong><br>
  Graph · Trace · Agent Communication · Governance · Evidence
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0">
  <img src="https://img.shields.io/badge/graph%20schema-1.0.0-purple" alt="Graph schema 1.0.0">
  <img src="https://img.shields.io/badge/tests-78%2F78%20passing-brightgreen" alt="78 of 78 tests passing">
  <img src="https://img.shields.io/badge/MCP-stdio%20%2B%20HTTP-7a2cff" alt="MCP stdio and HTTP">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+"><br>
  <img src="https://img.shields.io/badge/status-v1.0%20local%20release-success" alt="v1.0 local release">
  <img src="https://img.shields.io/badge/provider-agnostic-informational" alt="Provider agnostic">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

> **One strand. End to end.**

Skein is an engineering context, execution, governance and evidence layer for AI-driven software development. It turns a repository and its surrounding engineering knowledge into a **versioned graph**, exposes targeted context to agents, connects agent execution to quality evidence, and provides an explicit **AI-DLC Control Plane** for governed lifecycle decisions.

Skein is deliberately **not another coding agent**. It is the continuous thread underneath agents: the layer that helps them understand the system, share context, preserve traceability, operate under governance, and produce reproducible evidence.

> **Current release: v1.0.0 — AI-DLC Control Plane.**
>
> v0.7 introduced real agent execution, v0.8 adaptive context intelligence, v0.9 the autonomous quality loop, and v1.0 connects those capabilities into one governed lifecycle.

---

## Current status

| Area | Status | Notes |
|---|---|---|
| Skein software | 🟢 **v1.0.0** | AI-DLC Control Plane release |
| Graph contract | 🟢 **v1.0.0** | Independently versioned from software |
| Automated tests | 🟢 **78/78 passing** | Local release validation |
| MCP | 🟢 **Available** | JSON-RPC stdio + HTTP endpoint |
| Adaptive context | 🟢 **Available** | Deterministic, budget-aware selection |
| Autonomous quality loop | 🟢 **Available** | Bounded retry/evaluation loop |
| Provider bridges | 🟢 **Available** | OpenAI and Anthropic bridge contracts |
| Governance | 🟢 **Available** | RBAC, approvals, audit, sandbox boundaries |
| Enterprise integrations | 🟡 **Next phase** | Git/CI/Jira/SSO integrations remain deployment work |
| Production-scale SaaS | 🟡 **Not claimed by v1.0** | v1.0 is a runnable local control-plane implementation |

These labels describe the repository's current implementation status. They are not a claim that every enterprise integration is production-certified.

---

# What is Skein?

The name comes from a **skein**: a loosely coiled length of thread that can be unwound and followed as one continuous strand.

That is the architectural idea behind Skein.

Modern AI-assisted engineering often breaks context into isolated pieces:

```text
Requirement → Planner → Coder → Tester → Reviewer
                  ↓        ↓        ↓
               context  context  context
               rebuilt  rebuilt  rebuilt
```

Skein connects those pieces:

```text
                         SKEIN
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
      GRAPH              TRACE        AGENT COMMUNICATION
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                 Adaptive Context
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          Planner         Coder        Tester
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                   Autonomous Quality
                           │
                    Governance Gate
                           │
                  Human Approval / Policy
                           │
                           ▼
                        Evidence
```

The result is a persistent engineering thread connecting **what the system is, why it exists, what changed, what agents did, how quality was evaluated, and what evidence supports the outcome**.

---

# Why do we need Skein?

AI coding tools are increasingly capable, but capability alone does not solve the engineering-context problem.

### Agents need system context, not just files

A repository contains relationships that agents repeatedly have to reconstruct:

- callers and callees
- dependencies
- tests and requirements
- tickets and architectural decisions
- affected components
- historical changes
- quality evidence

Skein turns these relationships into a queryable engineering graph.

### Multi-agent workflows lose context

Planner, coder, tester and reviewer agents can each receive overlapping context. Skein provides a shared context substrate and an MCP-compatible interface so the context can be retrieved rather than reconstructed independently.

### AI execution needs an evidence trail

A model response is not engineering evidence. Skein records context selection, execution telemetry, traceability, quality signals, lifecycle events and approval decisions separately so they can be audited.

### AI productivity needs measurement

Skein supports matched Baseline/Skein evaluation, deterministic experiment assignment, token/cost telemetry and evidence grading. It is designed to say **“insufficient evidence”** rather than manufacture a productivity claim.

---

# Skein vs. other libraries and platforms

Skein is **complementary** to agent frameworks, RAG libraries, parsers and IDE assistants. The differentiator is the combination of a persistent engineering graph, adaptive context, agent execution evidence, autonomous quality feedback and a governed AI-DLC lifecycle.

The table below is a **positioning comparison, not a benchmark or an exhaustive feature matrix**. Capabilities of external projects evolve independently of Skein.

| Solution / category | Primary center of gravity | Engineering graph as system of record | Versioned trace & evidence | Adaptive context | Autonomous quality loop | AI-DLC governance |
|---|---|---:|---:|---:|---:|---:|
| **Skein** | AI-DLC context + evidence + control plane | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| **LangGraph** | Stateful agent/workflow orchestration | Partial / application-defined | Partial / application-defined | Application-defined | Application-defined | Application-defined |
| **LlamaIndex** | Data/RAG and knowledge access | Optional knowledge graphs | Partial / application-defined | Retrieval-focused | Not its primary role | Not its primary role |
| **AutoGen** | Multi-agent conversation/orchestration | No dedicated engineering graph | Application-defined | Application-defined | Application-defined | Application-defined |
| **CrewAI** | Role-based agent crews/workflows | No dedicated engineering graph | Application-defined | Application-defined | Application-defined | Application-defined |
| **MCP SDK / MCP server** | Tool/context interoperability protocol | No | No | No | No | Client/server policy-dependent |
| **Tree-sitter** | Source parsing / syntax trees | No lifecycle graph | No | No | No | No |
| **Vector databases** | Similarity retrieval | No engineering semantics by default | No lifecycle evidence | Retrieval primitive | No | No |
| **AI coding IDEs** | Developer interaction + code generation | Usually workspace/index oriented | Usually tool/session oriented | Yes, IDE-specific | Varies | Varies |

### The practical differentiator

Skein does **not** try to replace these systems. It can sit above or beside them:

```text
             IDE / Coding Agent / Agent Framework
                          │
                          │ MCP / SDK / CLI
                          ▼
                ┌──────────────────────┐
                │        SKEIN         │
                │                      │
                │ Graph                │
                │ Trace                │
                │ Context Intelligence │
                │ Quality Loop         │
                │ Evidence             │
                │ Governance           │
                │ Control Plane        │
                └──────────┬───────────┘
                           │
                     CI / Tests / Review
```

**Think of LangGraph/CrewAI/etc. as places where agents can be orchestrated; think of Skein as the engineering thread that gives those agents durable system context, traceability, evidence and governance.**

---

# Architecture

Skein is built as complementary layers rather than a single monolithic agent.

```text
┌──────────────────────────────────────────────────────────────┐
│                     AI-DLC CONTROL PLANE                     │
│ Specify → Plan → Context → Execute → Evaluate → Approve     │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                AUTONOMOUS QUALITY LOOP                       │
│ Execute → Observe → Evaluate → Learn → Re-select → Retry     │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│              ADAPTIVE CONTEXT INTELLIGENCE                   │
│ Relevance · Graph connectivity · Feedback · Token budget     │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                   AGENT / MCP LAYER                          │
│ CLI · Provider Bridges · MCP stdio · MCP HTTP                │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    ENGINEERING GRAPH                         │
│ Files · Functions · Classes · Requirements · Tickets · Tests │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                VERSIONING + SDD + EVIDENCE                   │
│ Commits · Diffs · Traceability · Telemetry · Audit · RBAC    │
└──────────────────────────────────────────────────────────────┘
```

The key design principle is that **context, communication, execution evidence and governance are one engineering substrate rather than disconnected add-ons**.

---

# v1.0 AI-DLC Control Plane

The control plane is the orchestration layer introduced in v1.0. It does not replace the graph, adaptive context engine, provider bridges or quality loop; it coordinates them.

## Lifecycle

```text
Specify
   ↓
Plan
   ↓
Select Context
   ↓
Execute
   ↓
Observe
   ↓
Evaluate
   ↓
Approval Required ──→ Rejected
   ↓
Approved
   ↓
Finalize
   ↓
Evidence Package
```

The persistent state machine is:

```text
created → planned → executing → evaluating → approval_required → approved → completed
```

Failure, rejection and cancellation are terminal states. Invalid transitions are rejected.

### Governance boundaries

- risk is explicit: `low`, `medium`, `high`, `critical`
- approval is attributable to an actor
- quality evidence is separate from provider success
- lifecycle events are append-only JSONL
- exports receive a deterministic integrity fingerprint
- the control plane does not silently mutate source code
- existing policy and sandbox boundaries remain in force

### Control-plane CLI

```bash
skein control-init . \
  --task-id PAY-142 \
  --title "Add payment authorization" \
  --description "Implement authorization workflow" \
  --spec SKN-001 \
  --risk high

skein control-plan .
skein control-begin .
skein control-evaluate . --passed --score 0.95 --execution-id EXEC-123
skein control-approve . --actor reviewer-1 --reason "Quality evidence reviewed"
skein control-finalize .
skein control-status .
skein control-export .
```

If approval is not required for a low-risk flow, the run can be created with `--no-approval`, subject to the configured policy.

---

# How to use Skein as an MCP server

Skein exposes a lightweight, provider-neutral MCP-compatible JSON-RPC server in two local modes.

## 1. Stdio — recommended for local IDEs

From the project root:

```bash
skein init .
skein ingest .
skein mcp-stdio .
```

The process communicates over stdin/stdout and is intended to be started by an MCP client. Do **not** launch it in a terminal and expect a normal interactive prompt; the client owns the protocol stream.

Available tools include:

| Tool | Purpose |
|---|---|
| `query_graph` | Search the shared engineering graph |
| `get_subgraph` | Retrieve a node neighborhood |
| `get_traceability` | Retrieve links for specs/commits |
| `get_diff` | Compare graph versions |
| `propose_node` | Create a governed graph proposal |
| `propose_edge` | Create a governed graph proposal |
| `commit_proposal` | Commit an approved proposal |

Write operations require an authenticated identity and policy authorization. Reviewer/admin identities are required for proposal commits.

## 2. HTTP — useful for shared/dev environments

```bash
skein mcp-http . --host 127.0.0.1 --port 8765
```

The MCP endpoint is:

```text
POST http://127.0.0.1:8765/mcp
GET  http://127.0.0.1:8765/health
```

The HTTP adapter accepts `X-Skein-Identity` for identity-scoped operations. Keep the endpoint bound to localhost unless you have explicitly placed it behind an authenticated, policy-controlled network boundary.

### MCP security model

Skein intentionally separates **read context** from **write proposals**:

```text
Agent / IDE
    │
    ├── read graph ────────────────► allowed by read policy
    │
    ├── propose change ────────────► identity + policy
    │
    └── commit proposal ───────────► reviewer/admin gate
```

Skein does not store provider API keys in graph telemetry and does not turn model-generated shell commands into privileged execution.

---

# IDE integration

Skein does not require a custom IDE extension for the core integration. **MCP is the integration boundary.** Any MCP-capable IDE/client can consume the Skein tools.

## VS Code + GitHub Copilot / Agent mode

Current VS Code releases support workspace MCP configuration in `.vscode/mcp.json`. A local Skein configuration can be as small as:

```json
{
  "servers": {
    "skein": {
      "type": "stdio",
      "command": "skein",
      "args": ["mcp-stdio", "${workspaceFolder}"]
    }
  }
}
```

Then:

1. Open the repository in VS Code.
2. Create `.vscode/mcp.json` with the configuration above.
3. Ensure `skein` is on your PATH, or replace `command` with the absolute executable path.
4. Run **MCP: List Servers** to confirm Skein starts.
5. Open Agent/Chat mode and enable the Skein tools.
6. Ask questions such as:

```text
What functions are affected by the checkout change?
Which tests cover create_order?
Show me the graph neighborhood around payment authorization.
Compare the current graph with the previous commit.
```

The IDE remains the coding surface; Skein supplies durable engineering context and governed graph operations.

Ready-to-copy examples are included in `examples/mcp/`, including a VS Code `.vscode/mcp.json` configuration and a generic `mcpServers` configuration.

> VS Code's MCP configuration and trust model evolve independently of Skein. Treat the client-specific configuration above as the current workspace pattern and verify the client version when deploying it.

## Other MCP-capable IDEs and agent clients

The same local stdio server can be registered with clients that use the common `mcpServers` configuration shape:

```json
{
  "mcpServers": {
    "skein": {
      "command": "skein",
      "args": ["mcp-stdio", "/absolute/path/to/project"]
    }
  }
}
```

Client configuration names and locations vary. The invariant is the command:

```bash
skein mcp-stdio /absolute/path/to/project
```

For remote/shared use, point the client at the HTTP `/mcp` endpoint and provide the identity/authentication mechanism required by the deployment.

---

# Greenfield project: first Skein project from zero

Greenfield projects benefit from introducing Skein **before** the codebase becomes large.

## Step 1 — create the project

```bash
mkdir checkout-service
cd checkout-service
python -m venv .venv
source .venv/bin/activate
pip install -e /path/to/skein
```

If Skein itself is being installed from a package rather than a source checkout, use the normal package installation method instead.

## Step 2 — initialize the engineering thread

```bash
skein init .
skein spec-check .
```

Create the first machine-readable requirements/specification clauses under `spec/clauses/` and keep each clause bounded to the increment you can actually verify.

## Step 3 — build a thin vertical slice

For example:

```text
Requirement
   ↓
API contract
   ↓
Implementation
   ↓
Unit/integration test
   ↓
Quality evidence
```

Then ingest the repository:

```bash
skein ingest . --message "initial checkout vertical slice"
```

Inspect the graph:

```bash
skein query . "checkout"
skein trace . --spec SKN-001
```

## Step 4 — use adaptive context

```bash
skein context-select --task-id checkout-001 \
  --query "validate checkout payment authorization" \
  --budget 1200

skein context-render --task-id checkout-001 \
  --query "validate checkout payment authorization" \
  --budget 1200
```

## Step 5 — run a governed AI-DLC task

```bash
skein control-init . \
  --task-id checkout-001 \
  --title "Implement payment authorization" \
  --description "Authorize a checkout payment before order confirmation" \
  --spec SKN-001 \
  --risk medium

skein control-plan .
skein control-begin .
```

Execute the approved agent workflow through the adapter/runtime, run the real tests, then record objective quality evidence:

```bash
skein control-evaluate . --passed --score 0.96
skein control-approve . --actor engineer-1 --reason "Tests and review passed"
skein control-finalize .
```

Finally export the evidence:

```bash
skein control-export . > evidence.json
```

### Greenfield principle

Do not create a giant specification for the entire future product. Build one verifiable vertical slice at a time. The spec's blast radius should not exceed what the current increment can validate.

---

# Brownfield project: introducing Skein into an existing system

Brownfield adoption is intentionally different. The existing code is **observed behavior**, not automatically authoritative requirements.

## Step 1 — initialize without changing application code

From the existing repository:

```bash
cd existing-service
skein init .
skein ingest . --message "baseline brownfield graph"
```

Review the resulting graph and communities before asking an agent to modify anything:

```bash
skein query . "payment"
skein communities .
skein history .
```

## Step 2 — classify what you discover

Treat reverse-engineered behavior as evidence with different trust levels:

- **Corroborated:** code + meaningful test/docs/human confirmation agree.
- **Plausible but unverified:** behavior exists but intent is unclear; characterize it before treating it as a requirement.
- **Suspicious legacy behavior:** likely accidental or dangerous; do not promote it to an authoritative requirement without a decision.

This prevents Skein from turning every legacy quirk into a permanent specification.

## Step 3 — start with one bounded context

Pick one business-critical but containable area. Add or refine the relevant SDD clauses and characterization tests. Then re-ingest:

```bash
skein ingest . --message "characterize payment behavior"
skein spec-check .
skein trace . --spec SKN-001
```

## Step 4 — introduce MCP to the IDE

Configure the repository's MCP client to run:

```bash
skein mcp-stdio /absolute/path/to/existing-service
```

Now the coding agent can ask Skein for the structural neighborhood before proposing a change instead of reconstructing the whole legacy system in its prompt.

## Step 5 — use the quality loop conservatively

For a risky legacy change, let the agent work within a bounded task and feed actual test/static-analysis results into the quality evaluator. If quality fails, the v0.9 loop can re-select context and retry within an explicit iteration budget.

## Step 6 — keep the old system behind a boundary

For substantial migrations, use an anti-corruption/translation boundary so newly verified behavior does not inherit every legacy quirk automatically.

### Brownfield principle

**Observed behavior is not automatically intent.** Skein gives you the graph and evidence needed to separate what the system does from what the organization has decided it should do.

---

# Testing Skein itself

Run the full local test suite:

```bash
pytest -q
```

Expected v1.0 release baseline:

```text
78 passed
```

Run the release/security checks:

```bash
skein release-check .
skein hardening .
skein certify .
skein verify .
```

Generate the local control panel:

```bash
skein dashboard .
```

Then open:

```text
.skein/dashboard.html
```

The panel is self-contained and embeds the Skein logo; it does not require an external image host.

---

# Graph contract

The current graph contract is independently versioned as **Graph Schema v1.0.0**.

### Node types

- `File`
- `Function`
- `Class`
- `Requirement`
- `Ticket`
- `ADR`
- `TestCase`

### Edge types

- `CALLS`
- `IMPORTS`
- `JUSTIFIES`
- `TESTS`
- `EXTRACTED`
- `INFERRED`

The schema lives outside implementation code so ingestion, querying, versioning, compression and agent integrations share the same contract.

---

# Adaptive Context Intelligence — v0.8

v0.8 moved Skein from **context provider** to **context selector**.

The selector ranks engineering evidence using a transparent first-generation model:

```text
score =
    0.72 × lexical relevance
  + 0.18 × graph connectivity
  + 0.10 × bounded feedback
```

A diversity bonus is applied during greedy selection. Selection is deterministic, budget-aware and persisted as append-only evidence.

CLI:

```bash
skein context-select --task-id T1 --query "create order payment" --budget 1200
skein context-render --task-id T1 --query "create order payment" --budget 1200
skein context-feedback --selection-id <id> --node function:create_order --reward 1 --task-id T1
skein context-health
```

This is **adaptive retrieval, not autonomous reinforcement learning**. Explicit feedback is bounded and auditable.

---

# Autonomous Quality Loop — v0.9

v0.9 closes the adaptive-context loop:

```text
Task
 ↓
Select context
 ↓
Execute agent
 ↓
Observe
 ↓
Evaluate engineering quality
 ↓
Learn bounded relevance feedback
 ↓
Re-select context
 ↓
Retry or stop
```

Guardrails include:

- explicit maximum iterations
- injectable quality evaluator
- bounded feedback `[-1, 1]`
- append-only loop evidence
- execution/context/quality fingerprints
- explicit stop reasons
- no autonomous source-code mutation by Skein itself

A provider API success is **not** treated as proof that the engineering task succeeded.

---

# Agent execution and provider bridges

Skein v0.7 introduced a provider-neutral adapter layer and concrete bridges for:

- OpenAI Responses API / Chat Completions-compatible clients
- Anthropic Messages-compatible clients
- generic SDK callables
- controlled CLI/argv execution

Provider SDKs remain optional. Credentials and provider client lifecycle stay outside Skein core.

The evidence flow is:

```text
AgentRequest
   ↓
Provider / CLI adapter
   ↓
Normalized AgentResult
   ↓
ConnectorEvent
   ↓
Evaluation / Evidence
```

---

# Traceability and evidence

Skein connects engineering intent to implementation and verification.

```text
Requirement
    │
    ├── JUSTIFIES ──> Function / File
    │                    │
    │                    └── CALLS ──> Function
    │
    └── TESTS ────────> TestCase
```

Useful questions include:

- What code implements this requirement?
- What tests cover this change?
- Which requirements are affected by this file?
- What changed between graph versions?
- Which agent performed the action?
- What quality evidence supports the outcome?
- Who approved the final decision?

---

# Compression and measurement

Skein's verified compression layer reduces unnecessary context while preserving load-bearing code, commands and errors. The Stage 1 commerce fixture demonstrated approximately **95% context reduction with 100% structural retrieval F1** for the evaluated fixture.

These are local benchmark results, not a production LLM savings claim. Real-world effectiveness should be established with matched agent experiments.

The v0.5 evaluation engine supports metrics such as:

- context tokens
- cost
- latency
- rework
- handoff loss
- task outcome / success guardrails

Evidence grades intentionally distinguish strong evidence from insufficient evidence.

---

# Governance and safety

Current controls include:

- identity-scoped agent actions
- proposal/approval separation
- reviewer/admin commit gates
- audit records
- policy enforcement
- sandbox controls
- secret scanning
- integrity verification
- replay protection
- explicit evidence boundaries
- controlled argv execution with `shell=False`

The design principle is:

> **Agents may accelerate engineering decisions without silently becoming the authority for those decisions.**

---

# Local dashboard / Control Panel

Skein v1.0 includes a self-contained HTML dashboard generated from the local workspace:

```bash
skein dashboard .
```

It includes Skein branding, graph/history information, telemetry, compression health, control-plane state and governance posture.

The control panel is intentionally local and dependency-light. It is a visibility surface over the evidence already persisted by Skein; it is not a replacement for the control-plane APIs.

---

# FAQ

### Is Skein another coding agent?

No. Skein is the context, evidence, execution and governance layer around agents. Agents can remain replaceable.

### Is Skein a RAG library?

Not primarily. Retrieval is one capability. Skein's distinctive unit is **engineering evidence connected to a versioned graph and lifecycle state**, not a generic document/vector index.

### Does Skein replace LangGraph, CrewAI, AutoGen or LlamaIndex?

No. Those systems can remain the agent/orchestration/retrieval layer. Skein can sit beside them through SDK adapters or MCP.

### Does Skein require an LLM?

No for core graph ingestion, querying, versioning, compression, governance, MCP and deterministic context selection. Provider execution bridges obviously require the relevant provider/client when you choose to run real models.

### Does Skein store my OpenAI or Anthropic API keys?

No. Provider credentials and provider client lifecycle remain outside Skein core.

### Can Skein modify my source code autonomously?

The v1.0 control plane does not silently mutate source code. Agent execution can be integrated, but repository mutation remains bounded by the external execution environment, policies and explicit workflow controls.

### What happens if the agent succeeds but the tests fail?

The provider invocation can be recorded as successful while the engineering quality gate fails. Skein keeps those signals separate and can stop or retry the quality loop.

### Can I use Skein with a brownfield application?

Yes. Brownfield is a primary use case. Start by ingesting and characterizing the existing system. Treat reverse-engineered behavior as evidence with trust levels rather than blindly promoting every legacy behavior to a requirement.

### Can I use Skein for a greenfield application?

Yes. Start with a small vertical slice: specification → implementation → tests → evidence. Grow the graph and specification incrementally.

### Does Skein require a vector database?

No. v0.8 adaptive selection is deterministic and graph-native. Vector databases can be added later as optional retrieval infrastructure.

### Does Skein require Kubernetes, Postgres or a cloud service?

No for the local implementation. The v1.0 bundle is designed to run locally. Enterprise deployment infrastructure is a future integration concern.

### Is the MCP implementation an official SDK implementation?

Skein provides a lightweight MCP-compatible JSON-RPC server and protocol artifacts. It is intentionally provider-neutral. The repository does not claim that every commercial MCP client/provider integration is officially certified.

### How do I know whether Skein actually improves engineering?

Run matched Baseline/Skein experiments, capture real task outcomes and quality evidence, and use the evaluation engine. Do not infer engineering improvement from token reduction alone.

### What is the most important idea behind Skein?

**The continuous thread.** Context, communication, execution, quality, traceability and governance should remain connected from specification to production evidence.

---

# Roadmap

## v1.0 — AI-DLC Control Plane — current

```text
Specify → Plan → Select Context → Execute → Evaluate → Approve → Finalize
```

Implemented:

- persistent AI-DLC lifecycle state machine
- append-only lifecycle event ledger
- explicit quality gate
- human approval gate
- deterministic evidence integrity fingerprint
- adaptive context integration
- autonomous quality-loop integration
- MCP context access
- provider-neutral execution bridges

## v1.1 — Enterprise Control Plane — next

The next phase should focus on real enterprise adoption rather than simply adding more agent features:

- GitHub/GitLab pull-request integration
- Jira/Azure DevOps traceability
- CI/CD quality gates
- real test-result ingestion
- policy-as-code expansion
- enterprise identity / SSO
- organization/project isolation
- multi-repository graph federation
- production audit exports
- operational dashboards and alerts

## Longer term

- learned/hybrid context ranking
- production feedback and incident linkage
- richer agent marketplace/adapter ecosystem
- enterprise-scale multi-project governance
- AI-DLC control-plane interoperability

---

# Installation

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Run the suite:

```bash
pytest -q
```

Check the version:

```bash
skein version
```

Initialize a repository:

```bash
skein init .
```

Ingest it:

```bash
skein ingest .
```

---

# Repository structure

```text
skein/
├── skein/                    # Core Python implementation
│   ├── control_plane.py      # v1.0 AI-DLC lifecycle
│   ├── autonomous_loop.py    # v0.9 quality loop
│   ├── context_intelligence.py # v0.8 adaptive selection
│   ├── provider_bridges.py   # Provider execution bridges
│   ├── agent_adapters.py     # Provider-neutral adapters
│   ├── agent_runtime.py      # Controlled execution
│   ├── mcp/                  # MCP-compatible server
│   ├── ingestion/            # Graph construction
│   ├── sdd/                  # Specification / traceability
│   ├── governance/           # Policy and sandbox controls
│   └── assets/               # Embedded Skein branding
├── assets/                   # Repository branding assets
├── schemas/                  # Versioned graph/control-plane contracts
├── spec/                     # Machine-readable SDD clauses
├── tests/                    # Automated tests
├── eval/                     # Evaluation fixtures
├── docs/                     # Architecture and release documentation
├── packages/                 # Protocol/package artifacts
├── benchmarks/               # Benchmark fixtures and results
└── README.md
```

---

# Design principles

### 1. Context is an engineering asset

Context should be structured, queryable, versioned and reusable.

### 2. The graph is not the product by itself

The value comes from connecting graph knowledge to agent workflows, traceability and evidence.

### 3. Agents should be replaceable

Skein remains provider- and agent-neutral rather than hard-coding the architecture around one model vendor.

### 4. Governance is part of execution

Approval, identity, auditability and policy controls exist alongside agent capabilities.

### 5. Evidence must be reproducible

Experiments and control-plane runs record enough provenance to understand how an outcome was produced and whether evidence was altered.

### 6. Do not confuse optimization with quality

Reducing tokens is useful only if engineering outcomes remain acceptable or improve.

### 7. Skein should be able to say “I don't know”

Missing telemetry, insufficient sample sizes and unresolved confounds remain visible rather than being converted into optimistic claims.

---

# Contributing

Skein is intended to evolve as an open engineering project.

Start with `CONTRIBUTING.md`, review the relevant design documentation under `docs/`, and add tests for behavioral changes.

Contributions are particularly valuable in:

- graph ingestion
- language/framework parsers
- agent adapters
- MCP integrations
- IDE/client integrations
- evaluation datasets
- experimental methodology
- governance policies
- benchmarks
- enterprise connectors
- documentation

---

# The idea in one sentence

> **Skein is the continuous thread that connects engineering knowledge, agent context, agent communication, traceability, governance and evidence across the AI-driven software lifecycle.**

---

## License

See the repository license and contribution documentation for the current project terms.