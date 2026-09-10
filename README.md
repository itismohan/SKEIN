# Skein

<p align="center">
  <img src="assets/skein-logo.png" alt="Skein — The Continuous Thread of AI-DLC" width="760">
</p>

**The Continuous Thread of AI-DLC**

> **Graph · Trace · Agent Communication**  
> **One strand. End to end.**

Skein is an engineering context and evidence layer for AI-driven software development. It turns a codebase and its surrounding engineering knowledge into a **versioned graph**, exposes that context to agents through a shared protocol, tracks what happened, and provides the controls needed to evaluate whether AI-assisted engineering actually improves outcomes.

Skein is deliberately not another coding agent. It is the **continuous thread underneath agents**: the layer that helps agents understand the system, share context, preserve traceability, operate under governance, and produce reproducible evidence.

---

## What is Skein?

The name comes from a **skein**: a loosely coiled length of thread that can be unwound and followed as one continuous strand.

That is the architectural idea behind Skein.

Modern AI-assisted engineering often breaks context into isolated pieces:

```text
Requirement → Developer → Code Agent → Test Agent → Reviewer
                  ↓           ↓             ↓
              separate     separate       separate
              context      context        context
```

Skein aims to connect those pieces:

```text
                         SKEIN
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
      GRAPH              TRACE        AGENT COMMUNICATION
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                     Shared Context
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          Planner         Coder        Tester
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                     Reviewer / Human
                           │
                           ▼
                       Evidence
```

The result is a persistent engineering thread connecting **what the system is, why it exists, what changed, what agents did, and what evidence supports the result**.

---

# Why do we need Skein?

AI coding tools are becoming increasingly capable, but capability alone does not solve the engineering-context problem.

### 1. Agents see artifacts, not always the system

A repository contains relationships that are easy for humans to infer but expensive to reconstruct repeatedly for an AI agent:

- which functions call which other functions
- which modules depend on one another
- which tests exercise a component
- which requirements justify a change
- which files are affected by a modification
- how a change propagates through the system

Skein constructs a machine-readable graph so agents can retrieve **targeted structural context** rather than repeatedly consuming large raw repository snapshots.

### 2. Agent context is repeatedly reconstructed

In multi-agent workflows, the planner, coder, tester and reviewer can repeatedly receive overlapping context.

Skein provides a shared context layer so the relevant engineering state can be referenced instead of reconstructed independently.

### 3. Context changes over time

A static knowledge base quickly becomes stale.

Skein versions its graph and records changes so an agent can reason about:

```text
What is true now?
What changed?
Why did it change?
What was true before?
```

### 4. AI decisions need traceability

For governed engineering environments, it is not enough to know that an agent produced an answer.

We need to know:

- what context it received
- what task it was performing
- which agent produced the result
- which agent handed work to another
- what changed
- what policies applied
- what evidence supports the outcome

Skein treats traceability as part of the engineering substrate.

### 5. AI improvements must be measured, not assumed

A smaller prompt does not automatically mean a better engineering outcome.

Skein therefore separates **optimization signals** from **outcome evidence** and provides an evaluation/control layer for matched experiments.

The principle is simple:

> **Do not claim that AI made engineering better until the evidence shows it.**

---

# What problem does Skein solve?

| Engineering problem | Skein capability |
|---|---|
| Fragmented repository knowledge | Versioned engineering graph |
| Repeated context reconstruction | Targeted graph retrieval |
| Large raw repository prompts | Verified context compression |
| Multi-agent context loss | Shared agent context via MCP-compatible protocol |
| Untraceable AI actions | Agent telemetry and traceability |
| Context drift | Graph/version history and diffs |
| Uncontrolled agent proposals | Governance and approval controls |
| AI cost opacity | Token/cost telemetry and dashboards |
| Weak experimental discipline | Experimental Control Plane |
| Unsupported AI productivity claims | Matched evaluation and evidence grading |

---

# The Skein architecture

Skein is built as a sequence of complementary layers rather than a single monolithic agent.

```text
┌──────────────────────────────────────────────────────────────┐
│                    AI-DLC / Engineering Agents              │
│ Planner · Coder · Tester · Reviewer · Other Agents          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                         Agent Communication
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    Skein Context Layer                       │
│ Graph Query · Subgraphs · Traceability · Compression         │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    Engineering Graph                        │
│ Files · Functions · Classes · Requirements · Tickets         │
│ ADRs · Tests · Calls · Imports · Tests · Justifications      │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                 Versioning & Specification                   │
│ Commits · Diffs · Traceability · SDD · Rollback              │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│               Telemetry · Governance · Evidence              │
│ Audit · RBAC · Policies · Cost · Evaluation · Experiments    │
└──────────────────────────────────────────────────────────────┘
```

The key design principle is that **context, communication, execution evidence and governance should not be separate afterthoughts**.

---

# What does Skein know?

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

The schema lives outside implementation code so ingestion, querying, versioning, compression and agent integrations can share the same contract.

---

# How do we use Skein?

There are two complementary ways to think about usage.

## A. Use Skein as an engineering context layer

Start with a repository:

```bash
skein init .
skein ingest .
```

Then inspect or query the resulting engineering graph:

```bash
skein query . "checkout"
skein communities .
```

The exact query vocabulary depends on the graph content and supported CLI commands.

### Typical flow

```text
Repository
    ↓
Ingestion
    ↓
Engineering Graph
    ↓
Targeted Query / Subgraph
    ↓
Compressed Context
    ↓
Agent
```

Instead of giving an agent the entire repository, the application can provide the **smallest useful structural context** for the task.

---

## B. Use Skein to measure AI engineering workflows

Skein v0.5 introduced matched baseline-vs-Skein evaluation.

Skein v0.6 adds an **Experimental Control Plane** around that evaluation.

A controlled study can begin with:

```bash
skein experiment-init . --experiment-id my-study --seed 42
```

Register tasks:

```bash
skein experiment-add-task . \
  --task-id checkout-001 \
  --description "Add validation for checkout requests" \
  --difficulty medium
```

Create deterministic assignments:

```bash
skein experiment-assign .
```

Inspect the experiment:

```bash
skein experiment-status .
skein experiment-report .
```

Verify the manifest:

```bash
skein experiment-verify .
```

For paired-study sample-size planning:

```bash
skein experiment-power --stddev 10 --effect 3
```

Package the evidence record:

```bash
skein experiment-package .
```

### Important boundary

The v0.6 control plane **does not execute arbitrary agents and does not manufacture experimental outcomes**.

It establishes reproducible study design, assignment, provenance and evidence packaging. Actual agent execution and outcome telemetry must come from the real workflow.

---

# A practical AI-DLC workflow with Skein

A future production workflow can look like this:

```text
1. Requirement / Ticket
          ↓
2. Skein Graph Context
          ↓
3. Planner Agent
          ↓
4. Shared Context / Handoff
          ↓
5. Coding Agent
          ↓
6. Tests + Quality Checks
          ↓
7. Reviewer Agent / Human Review
          ↓
8. Graph + Trace Update
          ↓
9. Telemetry + Evidence
          ↓
10. Evaluation / Release Decision
```

The important difference is that Skein is not trying to replace every agent.

It provides the **thread connecting them**.

---

# Multi-agent communication

Skein provides a lightweight MCP-compatible protocol layer for shared engineering context.

The protocol exposes capabilities such as:

- graph querying
- subgraph retrieval
- traceability retrieval
- graph diffs
- controlled node proposals
- controlled edge proposals
- governed proposal commits

Identity-scoped roles and approval controls can be used to distinguish planning, coding, testing, reviewing and administrative actions.

Skein's current implementation is intentionally lightweight and provider-neutral; the reference adapters are not presented as official integrations with any particular commercial coding agent.

---

# Traceability

Skein is designed to connect engineering intent to implementation and verification.

For example:

```text
Requirement
    │
    ├──── JUSTIFIES ────> Function
    │                       │
    │                       └──── CALLS ────> Function
    │
    └──── TESTS ─────────> TestCase
```

This enables questions such as:

- What code implements this requirement?
- What tests cover this change?
- Which requirements are affected by this file?
- What changed between two graph versions?
- What evidence supports the change?

---

# Context compression

Raw repository context can be expensive and noisy.

Skein's compression layer is designed to preserve task-relevant information while reducing unnecessary context.

The current local benchmark on the commerce fixture demonstrated approximately **95% context reduction with 100% structural retrieval F1** for the evaluated fixture.

These are **local benchmark results, not a production LLM savings claim**. Real-world effectiveness must be established with matched agent experiments.

---

# Evidence over anecdotes

Skein v0.5 introduced an evaluation engine that compares matched Baseline and Skein executions.

Metrics include:

- context tokens
- cost
- latency
- rework
- handoff loss
- task outcome / success guardrails

Evidence is graded rather than automatically declared successful.

```text
30+ paired tasks + supported improvement + guardrail pass
                         ↓
                       Grade A

10+ paired tasks + supported improvement + guardrail pass
                         ↓
                       Grade B

Paired evidence, incomplete statistical gate
                         ↓
                       Grade C

No matched evidence
                         ↓
                       Grade D
```

This is intentional: **Skein should be capable of saying “insufficient evidence.”**

---

# Experimental Control Plane — v0.6

v0.6 adds the study infrastructure needed to make engineering experiments reproducible.

It provides:

- task corpus registration
- deterministic seeded assignment
- baseline/Skein allocation
- cohort support
- repository/environment fingerprints
- study provenance
- explicit confound reporting
- sample-size planning guidance
- manifest verification
- tamper-evident evidence packaging

A typical lifecycle is:

```text
Experiment Definition
        ↓
Task Corpus
        ↓
Deterministic Assignment
        ↓
Real Agent Execution
        ↓
Telemetry
        ↓
Matched Evaluation
        ↓
Evidence Package
        ↓
Engineering Decision
```

The control plane improves experimental rigor; it does not turn a local experiment into proof of production causality.

---

# Governance and safety

Skein treats governance as part of the engineering workflow.

Current capabilities include:

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

The design principle is:

> **Agents may accelerate engineering decisions without silently becoming the authority for those decisions.**

---

# Telemetry and AI FinOps

Skein can normalize agent telemetry across providers and workflows.

The connector layer supports provider-neutral event capture, including usage and cost information where supplied by the provider.

This makes it possible to analyze:

```text
Cost
 ├── Experiment
 ├── Task
 ├── Agent
 ├── Model
 └── Workflow

Usage
 ├── Input tokens
 ├── Output tokens
 └── Reasoning tokens where available
```

The purpose is not merely cost reporting. Cost can be evaluated alongside **quality, latency, rework and outcome**.

---

# Current status

## v0.6.0 — Experimental Control Plane

**Status: Release candidate / validated local implementation**

Implemented across the Skein roadmap:

- Stage 0 — project setup and scaffolding
- Stage 1 — ingestion and graph construction
- Stage 2 — versioned store and diffing
- Stage 3 — verified compression
- Stage 4 — shared-agent MCP protocol
- Stage 5 — dashboard and governance
- Stage 6 — hardening, packaging and release
- v0.3 — pilot intelligence
- v0.4 — agent connector layer
- v0.5 — evaluation and evidence engine
- **v0.6 — experimental control plane**
- **v0.7 — real agent execution & adapters**

The software version and graph schema version are independent:

```text
Skein software: 0.7.0
Graph schema:   1.0.0
```

See the release documentation under `docs/` for implementation-specific details.

---

# Roadmap

Skein's next phase is deliberately focused on proving value with real agent workflows rather than adding features for their own sake.

### v0.7 — Real Agent Execution & Adapters

**Current milestone.** v0.7 connects the v0.6 experiment protocol to real command-line agent workflows. The first adapter is deliberately provider-neutral: any agent that can be invoked as an explicit argv command can participate without giving Skein shell interpretation privileges.

- controlled Baseline/Skein execution
- assignment enforcement
- task + context injection through a deterministic environment envelope
- automatic execution telemetry
- task/context/command fingerprints
- timeout and process-failure capture
- evaluation-compatible results
- provider-specific SDKs can continue using the v0.4 connector layer
- concrete OpenAI and Anthropic provider execution bridges with normalized telemetry

Example:

```bash
skein experiment-init . --experiment-id commerce-pilot --seed 42
skein experiment-add-task . --task-id T1 --description "what calls checkout?"
skein experiment-assign .

skein agent-run . --task-id T1 --arm baseline \
  --command-json '["python","agent.py"]'

skein agent-run . --task-id T2 --arm skein \
  --command-json '["python","agent.py"]' \
  --context-query 'what calls checkout?'

skein agent-status .
skein evaluate .
```

The runtime always uses `shell=False`; it does not turn agent commands into shell scripts. The active execution environment remains responsible for sandboxing and network policy.

**Question:** Can agents actually use Skein end to end—and can we measure the result reproducibly?

### v0.8 — Adaptive Context Intelligence

Move from retrieving context to deciding what context is sufficient.

- context planning
- task-to-subgraph reasoning
- relevance scoring
- dependency-aware retrieval
- token-budget optimization
- stale/contradictory context detection

**Question:** Can Skein find the minimum sufficient context for successful work?

### v0.9 — Autonomous Quality Loop

Connect the continuous thread to engineering quality signals.

- impact analysis
- regression selection
- risk scoring
- automated quality gates
- test generation feedback
- production/operational feedback into the graph

**Question:** Can Skein improve the engineering feedback loop?

### v1.0 — Skein AI-DLC Control Plane

A production-oriented control plane connecting:

```text
Graph + Context + Agents + Trace + Evidence + Governance
```

**Question:** Can Skein become trusted infrastructure for AI-native software engineering?

---

# Installation

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Run the test suite:

```bash
pytest
```

Check the installed version:

```bash
skein version
```

Initialize a repository:

```bash
skein init .
```

---

# Repository structure

```text
skein/
├── skein/                    # Core Python implementation
├── schemas/                  # Versioned graph contracts
├── spec/                     # Specification / SDD material
├── tests/                    # Automated tests
├── eval/                     # Evaluation fixtures
├── docs/                     # Architecture and release documentation
├── packages/                 # Protocol/package artifacts
├── benchmarks/               # Benchmark fixtures and results
├── dist/                     # Release artifacts
└── README.md
```

---

# Design principles

### 1. Context is an engineering asset

Context should be structured, queryable, versioned and reusable.

### 2. The graph is not the product by itself

The value comes from connecting graph knowledge to agent workflows, traceability and evidence.

### 3. Agents should be replaceable

Skein is intended to remain provider- and agent-neutral rather than hard-coding the architecture around one model vendor.

### 4. Governance is part of execution

Approval, identity, auditability and policy controls should exist alongside agent capabilities.

### 5. Evidence must be reproducible

Experiments should record enough provenance to understand how a result was produced and whether the evidence was altered.

### 6. Do not confuse optimization with quality

Reducing tokens is useful only if engineering outcomes remain acceptable or improve.

### 7. Skein should be able to say “I don't know”

Missing telemetry, insufficient sample sizes and unresolved confounds should remain visible rather than being converted into optimistic claims.

---

# Contributing

Skein is intended to evolve as an open engineering project.

Start with `CONTRIBUTING.md`, review the relevant design documentation under `docs/`, and add tests for behavioral changes.

Contributions are particularly valuable in:

- graph ingestion
- language/framework parsers
- agent adapters
- MCP integrations
- evaluation datasets
- experimental methodology
- governance policies
- benchmarks
- documentation

---

# The idea in one sentence

> **Skein is the continuous thread that connects engineering knowledge, agent context, agent communication, traceability, governance and evidence across the AI-driven software lifecycle.**

---

## License

See the repository license and contribution documentation for the current project terms.
