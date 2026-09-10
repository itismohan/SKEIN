from pathlib import Path
import json
import typer
from . import __version__
from .schema import SCHEMA_VERSION
from .store import LocalGraphStore
from .ingestion.pipeline import IncrementalIngester
from .query import query as graph_query
from .watch import watch as run_watch
from .hook import install as install_hook
from .sdd import load_clauses, validate_clauses, TraceabilityStore, SDDIngestionPipeline
from .benchmarks import raw_context, graph_context, tokens, run_suite

app=typer.Typer(help="Skein — the continuous thread of AI-DLC.")

def commit_state(versioned):
    return versioned.graph
@app.command()
def version(): typer.echo(f"skein {__version__} | graph schema {SCHEMA_VERSION}")
@app.command()
def init(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    d=path/".skein"; d.mkdir(exist_ok=True)
    (d/"graph.json").write_text('{\n  "schema_version": "1.0.0",\n  "nodes": [],\n  "edges": []\n}\n')
    (d/"manifest.json").write_text('{"version":1,"files":{}}\n')
    typer.echo(f"Initialized Skein workspace: {d}")
@app.command()
def ingest(path:Path=typer.Argument(Path("."),exists=True,file_okay=False),full_rebuild:bool=False, author:str=typer.Option("ingest","--author"), message:str=typer.Option("ingest graph update","--message")):
    d=path/".skein"; d.mkdir(exist_ok=True); gp=d/"graph.json"
    history=d/"history"
    versioned=__import__("skein.versioning", fromlist=["VersionedGraphStore"]).VersionedGraphStore(history)
    if not versioned.head and gp.exists():
        base=LocalGraphStore.load(gp)
        versioned.graph=base.to_document()
        versioned.commit(versioned.graph, author="migration", message="import pre-versioned graph", spec_refs=("SKN-001",), expected_parent=None)
    r, commit = SDDIngestionPipeline(path, versioned=versioned).ingest_and_commit(author=author, message=message, full_rebuild=full_rebuild)
    if commit:
        gp.write_text(json.dumps(commit_state(versioned).to_contract(), indent=2)+"\n", encoding="utf-8")
        typer.echo(f"Ingestion committed: {commit.commit_id} parent={commit.parent_version}; +{r.added_files} added, {r.changed_files} changed, {r.unchanged_files} unchanged, -{r.removed_files} removed; {r.nodes} nodes, {r.edges} edges")
    else:
        gp.write_text(json.dumps(versioned.graph.to_contract(), indent=2)+"\n", encoding="utf-8")
        typer.echo(f"Ingestion unchanged: +{r.added_files} added, {r.changed_files} changed, {r.unchanged_files} unchanged, -{r.removed_files} removed; {r.nodes} nodes, {r.edges} edges")
@app.command("query")
def query_cmd(text:str, path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    store=LocalGraphStore.load(path/".skein"/"graph.json"); typer.echo(graph_query(store,text))
@app.command()
def communities(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    store=LocalGraphStore.load(path/".skein"/"graph.json"); import json; typer.echo(json.dumps(IncrementalIngester(path,store).community_hierarchy(),indent=2))
@app.command()
def watch(path:Path=typer.Argument(Path("."),exists=True,file_okay=False),interval:float=2.0): run_watch(path,interval)
@app.command()
def benchmark(path:Path=typer.Argument(Path("."),exists=True,file_okay=False),question:str=typer.Option("what calls main?")):
    """Compare whitespace-token counts for raw-file and graph-query context."""
    store=LocalGraphStore.load(path/".skein"/"graph.json")
    raw=raw_context(path,question); graph=graph_context(store,question)
    rt,gt=tokens(raw),tokens(graph); reduction=(1-gt/rt)*100 if rt else 0
    typer.echo(f"raw_tokens={rt} graph_tokens={gt} reduction={reduction:.2f}%")

@app.command("spec-check")
def spec_check(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Validate the machine-readable SDD contract and trust tiers."""
    clauses = load_clauses(path / "spec" / "clauses")
    validate_clauses(clauses)
    typer.echo(f"SDD contract valid: {len(clauses)} clauses")


@app.command("commit-graph")
def commit_graph_cmd(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    spec: list[str] = typer.Option([], "--spec", help="SDD clause ID; repeat for multiple clauses."),
    author: str = typer.Option("user", "--author"),
    message: str = typer.Option("graph mutation", "--message"),
):
    """Accept the current materialized graph through the SDD commit pipeline."""
    from .sdd import SDDCommitPipeline
    graph_path = path / ".skein" / "graph.json"
    if not graph_path.exists():
        raise typer.BadParameter(".skein/graph.json does not exist; run skein init/ingest first")
    from .schema import GraphDocument
    graph = GraphDocument.model_validate(json.loads(graph_path.read_text(encoding="utf-8")))
    history = path / ".skein" / "history"
    store = __import__("skein.versioning", fromlist=["VersionedGraphStore"]).VersionedGraphStore(history)
    pipeline = SDDCommitPipeline(store, path / "spec" / "clauses")
    commit = pipeline.commit(
        graph, author=author, message=message, spec_refs=spec, expected_parent=store.head
    )
    typer.echo(f"Committed graph: {commit.commit_id} parent={commit.parent_version} specs={','.join(commit.spec_refs)}")

@app.command("trace")
def trace_cmd(spec_ref: str | None = typer.Option(None, "--spec"), commit_id: str | None = typer.Option(None, "--commit"), path: Path = typer.Argument(Path("."), exists=True, file_okay=False)):
    """Inspect SDD traceability links between specs, tests, commits, and affected graph elements."""
    store = TraceabilityStore(path / ".skein" / "history")
    if spec_ref:
        links = store.for_spec(spec_ref)
    elif commit_id:
        links = store.for_commit(commit_id)
    else:
        links = store.links()
    typer.echo(json.dumps([l.__dict__ for l in links], indent=2))

@app.command("history")
def history_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), since:str|None=typer.Option(None,"--since"), since_date:str|None=typer.Option(None,"--since-date"), limit:int|None=typer.Option(None,"--limit")):
    """Show versioned graph commit history."""
    from .versioning import VersionedGraphStore
    store=VersionedGraphStore(path/".skein"/"history")
    typer.echo(json.dumps([c.__dict__ for c in store.history(since=since, since_date=since_date, limit=limit)], indent=2))

@app.command("conflicts")
def conflicts_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Show persisted optimistic-concurrency conflicts."""
    from .versioning import VersionedGraphStore
    store=VersionedGraphStore(path/".skein"/"history")
    typer.echo(json.dumps(store.conflicts(), indent=2))

@app.command("diff")
def diff_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), from_commit:str=typer.Option(...,"--from"), to_commit:str|None=typer.Option(None,"--to")):
    """Show deterministic structural diff between two graph versions."""
    from .versioning import VersionedGraphStore, diff_graphs
    store=VersionedGraphStore(path/".skein"/"history")
    before=store.state_at(from_commit)
    after=store.graph if to_commit is None else store.state_at(to_commit)
    typer.echo(json.dumps(diff_graphs(before, after), indent=2))

@app.command("rollback")
def rollback_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), target:str=typer.Option(...,"--to"), author:str=typer.Option("system","--author")):
    """Create a new commit restoring the graph to a prior known-good version."""
    from .versioning import VersionedGraphStore
    store=VersionedGraphStore(path/".skein"/"history")
    commit=store.rollback(target, author=author, spec_refs=("SKN-001",))
    gp=path/".skein"/"graph.json"; gp.write_text(json.dumps(store.graph.to_contract(), indent=2)+"\n", encoding="utf-8")
    typer.echo(f"Rollback committed: {commit.commit_id} parent={commit.parent_version} target={target}")

@app.command("pr-report")
def pr_report_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), base:str=typer.Option(...,"--base"), head:str|None=typer.Option(None,"--head"), output:Path|None=typer.Option(None,"--output")):
    """Generate the CI/PR structural diff report."""
    from .versioning import VersionedGraphStore
    from .pr_report import markdown_report
    text=markdown_report(VersionedGraphStore(path/".skein"/"history"), base, head)
    if output: output.write_text(text, encoding="utf-8"); typer.echo(f"PR report written: {output}")
    else: typer.echo(text)

@app.command("spec-list")
def spec_list(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """List active SDD clauses by trust tier."""
    clauses = load_clauses(path / "spec" / "clauses")
    validate_clauses(clauses)
    for clause in clauses:
        typer.echo(f"{clause.id}  Tier {clause.tier.value}  {clause.statement}")

@app.command("install-hook")
def hook(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)): typer.echo(f"Installed: {install_hook(path)}")
@app.command("benchmark-suite")
def benchmark_suite(path:Path=typer.Argument(Path("benchmarks/fixtures/commerce_service"),exists=True,file_okay=False), output:Path|None=typer.Option(None, "--output")):
    """Run the fixed Stage 1 repository benchmark and report token + retrieval metrics."""
    result=run_suite(path)
    text=json.dumps(result,indent=2)
    if output:
        output.write_text(text+"\n",encoding="utf-8")
        typer.echo(f"Benchmark report written: {output}")
    else:
        typer.echo(text)


@app.command("compress")
def compress_cmd(text: str, aggressiveness: str = typer.Option("balanced", "--aggressiveness")):
    """Compress prose with load-bearing checklist verification and safe fallback."""
    from .compression import compress, result_dict
    r=compress(text, aggressiveness=aggressiveness)
    typer.echo(json.dumps(result_dict(r), indent=2))

@app.command("mcp-stdio")
def mcp_stdio_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Run the lightweight MCP-compatible JSON-RPC stdio server."""
    from .mcp import serve_stdio
    serve_stdio(path)

@app.command("mcp-http")
def mcp_http_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), host:str=typer.Option("127.0.0.1"), port:int=typer.Option(8765)):
    """Run the remote HTTP MCP endpoint."""
    import uvicorn
    from .mcp.http import create_app
    uvicorn.run(create_app(path), host=host, port=port)

@app.command("compression-eval")
def compression_eval_cmd(path:Path=typer.Argument(Path("eval/compression_eval.json"),exists=True,file_okay=True)):
    """Run the verified-compression release gate."""
    from .compression.eval import run_eval
    result=run_eval(path); typer.echo(json.dumps(result,indent=2))
    if not result['passed']: raise typer.Exit(code=1)

@app.command("dashboard")
def dashboard_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), output:Path|None=typer.Option(None,"--output")):
    """Generate the Stage 5 local governance dashboard."""
    from .dashboard import write
    target=output or (path/".skein"/"dashboard.html")
    write(path,target)
    typer.echo(f"Dashboard written: {target}")

@app.command("audit-report")
def audit_report_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), output:Path|None=typer.Option(None,"--output"), commit_id:str|None=typer.Option(None,"--commit"), from_commit:str|None=typer.Option(None,"--from"), to_commit:str|None=typer.Option(None,"--to")):
    """Export a traceability + structural diff + compression verification audit report."""
    from .audit import generate
    text=generate(path,commit_id=commit_id,from_commit=from_commit,to_commit=to_commit)
    if output:
        output.write_text(text,encoding="utf-8")
        typer.echo(f"Audit report written: {output}")
    else:
        typer.echo(text)

@app.command("telemetry")
def telemetry_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Show Stage 5 agent-call cost telemetry."""
    from .telemetry import TelemetryStore
    typer.echo(json.dumps(TelemetryStore(path/".skein"/"history").aggregate(),indent=2))

@app.command("compression-health")
def compression_health_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Show compression verification health metrics."""
    from .compression.telemetry import CompressionTelemetry
    typer.echo(json.dumps(CompressionTelemetry(path/".skein"/"history").health(),indent=2))

@app.command("sandbox-check")
def sandbox_check_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Validate that a path/execution request is within Skein's conservative sandbox."""
    from .governance.sandbox import SandboxPolicy
    SandboxPolicy(path.resolve()).check_execution(subprocess=False,network=False)
    typer.echo("Sandbox policy: subprocess=DENY, network=DENY, path scope=ENFORCED")

@app.command("alerts")
def alerts_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), max_cost:float=typer.Option(1.0,"--max-cost"), max_fallback_rate:float=typer.Option(0.20,"--max-fallback-rate"), max_conflicts:int=typer.Option(5,"--max-conflicts")):
    """Evaluate Stage 5 anomaly thresholds."""
    from .alerts import evaluate
    alerts=evaluate(path,max_cost_usd=max_cost,max_fallback_rate=max_fallback_rate,max_conflicts=max_conflicts)
    typer.echo(json.dumps({"alerts":alerts,"passed":not alerts},indent=2))
    if alerts: raise typer.Exit(code=1)

@app.command("release-check")
def release_check_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Run offline Stage 6 release gates."""
    from .release import release_report
    report=release_report(path)
    typer.echo(json.dumps(report,indent=2))
    if not report["passed"]: raise typer.Exit(code=1)

@app.command("migrate")
def migrate_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Migrate a legacy materialized graph into versioned Skein history."""
    from .release import migrate_workspace
    typer.echo(json.dumps(migrate_workspace(path),indent=2))

@app.command("demo")
def demo_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Run a deterministic end-to-end MVP acceptance flow against a workspace."""
    from .release import release_report
    from .store import LocalGraphStore
    from .versioning import VersionedGraphStore
    from .sdd import SDDIngestionPipeline
    root=path.resolve(); (root/".skein").mkdir(exist_ok=True)
    versioned=VersionedGraphStore(root/".skein"/"history")
    result, commit=SDDIngestionPipeline(root, versioned=versioned).ingest_and_commit(author="demo",message="MVP acceptance ingestion",full_rebuild=True)
    if commit: (root/".skein"/"graph.json").write_text(json.dumps(versioned.graph.to_contract(),indent=2)+"\n")
    gates=release_report(Path(__file__).resolve().parents[1])
    payload={"ingestion":{"nodes":result.nodes,"edges":result.edges,"commit_id":commit.commit_id if commit else None},"release_gates":gates}
    typer.echo(json.dumps(payload,indent=2))
    if not gates["passed"]: raise typer.Exit(code=1)

@app.command("verify")
def verify_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)):
    """Verify append-only graph history integrity and materialized state."""
    from .integrity import verify_history
    result = verify_history(path)
    print(json.dumps({"passed": result.passed, "commits": result.commits, "head": result.head, "errors": list(result.errors)}, indent=2))
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("health")
def health_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Check local graph-store and version-history health."""
    from .health import check
    report=check(path); typer.echo(json.dumps(report,indent=2))
    if report["status"] != "ok": raise typer.Exit(code=1)

@app.command("acceptance")
def acceptance_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), output:Path|None=typer.Option(None,"--output")):
    """Run the deterministic offline MVP acceptance suite."""
    from .acceptance import run
    report=run(path)
    text=json.dumps(report,indent=2)
    if output:
        output.parent.mkdir(parents=True,exist_ok=True); output.write_text(text+"\n",encoding="utf-8"); typer.echo(f"Acceptance report written: {output}")
    else: typer.echo(text)
    if not report["passed"]: raise typer.Exit(code=1)

@app.command("certify")
def certify_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), output:Path|None=typer.Option(None,"--output")):
    """Run the offline interoperability and MVP certification suite."""
    from .mcp.certification import run_certification
    report=run_certification(path.resolve())
    text=json.dumps(report,indent=2)
    if output:
        output.parent.mkdir(parents=True,exist_ok=True); output.write_text(text+"\n",encoding="utf-8"); typer.echo(f"Certification report written: {output}")
    else: typer.echo(text)
    if not report["passed"]: raise typer.Exit(code=1)

@app.command("hardening")
def hardening_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), output:Path|None=typer.Option(None,"--output")):
    """Run the final local security, reliability, and release hardening suite."""
    from .hardening import run
    report=run(path.resolve())
    text=json.dumps(report,indent=2)
    if output:
        output.parent.mkdir(parents=True,exist_ok=True); output.write_text(text+"\n",encoding="utf-8"); typer.echo(f"Hardening report written: {output}")
    else: typer.echo(text)
    if not report["passed"]: raise typer.Exit(code=1)

@app.command("mcp-benchmark")
def mcp_benchmark_cmd(agents:int=typer.Option(3,"--agents")):
    """Measure duplicate context-building calls for shared graph vs baseline."""
    from .mcp.benchmark import measure_duplicate_context
    typer.echo(json.dumps(measure_duplicate_context(agents),indent=2))
@app.command("pilot-init")
def pilot_init_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), name:str=typer.Option("skein-design-partner-pilot","--name"), agents:int=typer.Option(3,"--agents")):
    """Create a deterministic design-partner pilot configuration."""
    from .pilot import init_pilot
    target=init_pilot(path.resolve(), name=name, agents=agents)
    typer.echo(f"Pilot configuration written: {target}")

@app.command("pilot-scenario-init")
def pilot_scenario_init_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), name:str=typer.Option("skein-design-partner-pilot","--name")):
    """Create an argv-only scenario template for matched baseline/Skein workflows."""
    from .pilot import init_scenario_pilot
    target=init_scenario_pilot(path.resolve(), name=name)
    typer.echo(f"Pilot scenario configuration written: {target}")

@app.command("pilot-scenario-run")
def pilot_scenario_run_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Run configured baseline/Skein workflows and capture objective execution signals."""
    from .pilot import run_scenario_pilot, write_scenario_result, render_scenario_report, SCENARIO_REPORT_NAME
    result=run_scenario_pilot(path.resolve())
    result_path=write_scenario_result(path.resolve(), result)
    report_path=path.resolve()/SCENARIO_REPORT_NAME
    report_path.write_text(render_scenario_report(result), encoding="utf-8")
    typer.echo(json.dumps({"result":str(result_path),"report":str(report_path),"runs":len(result["results"])},indent=2))

@app.command("pilot-run")
def pilot_run_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Run the local pilot baseline and Skein comparison."""
    from .pilot import run_pilot, write_pilot_result, write_pilot_report
    result=run_pilot(path)
    result_path=write_pilot_result(path, result)
    report_path=write_pilot_report(path, result)
    typer.echo(json.dumps({"passed": result["retrieval"]["f1"] >= 0.90 and (not result["compression"]["available"] or result["compression"]["passed"] is True), "result": str(result_path), "report": str(report_path), "context_reduction_pct": result["context_efficiency"]["token_reduction_pct"], "retrieval_f1": result["retrieval"]["f1"]}, indent=2))

@app.command("pilot-report")
def pilot_report_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), output:Path|None=typer.Option(None,"--output")):
    """Render the latest pilot results as Markdown."""
    from .pilot import REPORT_NAME, render_report
    result_path=path/".skein"/"pilot-results.json"
    if not result_path.exists():
        raise typer.BadParameter("No pilot results found; run skein pilot-run first")
    text=render_report(json.loads(result_path.read_text(encoding="utf-8")))
    target=output or (path/REPORT_NAME)
    target.write_text(text,encoding="utf-8")
    typer.echo(f"Pilot report written: {target}")



@app.command("connector-list")
def connector_list_cmd():
    """List installed provider-neutral Skein agent connectors."""
    from .connector import DEFAULT_REGISTRY
    typer.echo(json.dumps({"schema_version": __version__, "providers": DEFAULT_REGISTRY.providers()}, indent=2))

@app.command("connector-import")
def connector_import_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), source:Path=typer.Argument(...,exists=True,dir_okay=False), provider:str=typer.Option("generic","--provider"), experiment:str=typer.Option("skein","--experiment"), task_id:str=typer.Option(...,"--task-id"), agent:str=typer.Option(...,"--agent")):
    """Normalize provider events into the append-only Skein connector evidence stream."""
    from .connector import ingest_events, read_payload_jsonl
    result=ingest_events(path.resolve(), read_payload_jsonl(source.resolve()), provider=provider, experiment=experiment, task_id=task_id, agent=agent)
    typer.echo(json.dumps(result, indent=2))

@app.command("connector-summary")
def connector_summary_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Summarize normalized connector events by provider, event type and task."""
    from .connector import summarize
    typer.echo(json.dumps(summarize(path.resolve()), indent=2))

@app.command("telemetry-import")
def telemetry_import_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), source:Path=typer.Argument(...,exists=True,dir_okay=False)):
    """Import provider-neutral pilot telemetry JSONL into Skein's append-only store."""
    from .agent_telemetry import import_jsonl
    typer.echo(json.dumps(import_jsonl(path.resolve(), source.resolve()), indent=2))

@app.command("pilot-task-summary")
def pilot_task_summary_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Summarize paired baseline/Skein task telemetry."""
    from .agent_telemetry import summarize_tasks
    typer.echo(json.dumps(summarize_tasks(path.resolve()), indent=2))

@app.command("pilot-intelligence-init")
def pilot_intelligence_init_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), pilot:str=typer.Option("skein-v0.3-pilot","--pilot")):
    """Create the v0.3 Pilot Intelligence configuration."""
    from .pilot_intelligence import init_intelligence
    target=init_intelligence(path.resolve(), pilot=pilot)
    typer.echo(f"Pilot Intelligence configuration written: {target}")

@app.command("pilot-intelligence-run")
def pilot_intelligence_run_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Synthesize matched pilot scenarios, provider telemetry, quality, traceability and governance."""
    from .pilot_intelligence import run_intelligence, write_result, write_report
    root=path.resolve(); result=run_intelligence(root)
    result_path=write_result(root,result); report_path=write_report(root,result)
    typer.echo(json.dumps({"result":str(result_path),"report":str(report_path),"paired_scenarios":result["scenario_execution"]["paired_scenarios"],"production_quality_claim_allowed":result["evidence_quality"]["production_quality_claim_allowed"]},indent=2))

@app.command("pilot-intelligence-report")
def pilot_intelligence_report_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Render the latest v0.3 Pilot Intelligence report."""
    from .pilot_intelligence import REPORT_NAME, render_report
    result_path=path.resolve()/".skein"/"pilot-intelligence-results.json"
    if not result_path.exists(): raise typer.BadParameter("No Pilot Intelligence results found; run skein pilot-intelligence-run first")
    text=render_report(json.loads(result_path.read_text(encoding="utf-8")))
    target=path.resolve()/REPORT_NAME; target.write_text(text,encoding="utf-8"); typer.echo(f"Pilot Intelligence report written: {target}")

@app.command("evaluate")
def evaluate_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Run statistical matched-task evaluation with bootstrap confidence intervals."""
    from .evaluation import evaluate, write_result, write_report
    root=path.resolve(); result=evaluate(root); result_path=write_result(root,result); report_path=write_report(root,result)
    typer.echo(json.dumps({"result":str(result_path),"report":str(report_path),"paired_tasks":result["paired_tasks"],"evidence_grade":result["evidence_grade"],"claim_status":result["claim_status"]},indent=2))

@app.command("evaluation-init")
def evaluation_init_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Create v0.5 statistical evaluation configuration."""
    from .evaluation import init_evaluation
    typer.echo(f"Evaluation configuration written: {init_evaluation(path.resolve())}")

@app.command("evaluation-report")
def evaluation_report_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Render the latest v0.5 evaluation report."""
    from .evaluation import RESULT_NAME, REPORT_NAME, render_report
    root=path.resolve(); result_path=root/RESULT_NAME
    if not result_path.exists(): raise typer.BadParameter("No evaluation results found; run skein evaluate first")
    target=root/REPORT_NAME; target.write_text(render_report(json.loads(result_path.read_text(encoding="utf-8"))),encoding="utf-8")
    typer.echo(f"Evaluation report written: {target}")



@app.command("experiment-init")
def experiment_init_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), experiment_id:str=typer.Option("skein-v0.6-experiment","--experiment-id"), seed:int=typer.Option(42,"--seed")):
    """Initialize a reproducible v0.6 experimental control plane."""
    from .experiment import ExperimentConfig, save_config
    root=path.resolve(); config=ExperimentConfig(experiment_id=experiment_id,seed=seed,repository_commit=__import__('skein.experiment',fromlist=['repository_commit']).repository_commit(root))
    typer.echo(f"Experiment configuration written: {save_config(root,config)}")

@app.command("experiment-add-task")
def experiment_add_task_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), task_id:str=typer.Option(...,"--task-id"), description:str=typer.Option(...,"--description"), difficulty:str=typer.Option("medium","--difficulty")):
    """Register one task in the immutable experiment corpus."""
    from .experiment import TaskSpec, add_tasks
    typer.echo(json.dumps(add_tasks(path.resolve(),[TaskSpec(task_id=task_id,description=description,difficulty=difficulty)]),indent=2))

@app.command("experiment-assign")
def experiment_assign_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), cohort:str=typer.Option("default","--cohort")):
    """Deterministically randomize eligible tasks to baseline or Skein."""
    from .experiment import assign_tasks, load_config, create_manifest, write_manifest
    root=path.resolve(); result=create_manifest(root,assign_tasks(root,load_config(root),cohort)); write_manifest(root,result)
    typer.echo(json.dumps({"experiment_id":result["config"]["experiment_id"],"assignments":result["assignments"],"manifest_hash":result["manifest_hash"]},indent=2))

@app.command("experiment-status")
def experiment_status_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Show experiment corpus, assignment and confound status."""
    from .experiment import load_config, load_tasks, RESULT_NAME, verify_manifest
    root=path.resolve(); p=root/RESULT_NAME
    if not p.exists(): raise typer.BadParameter("No experiment assignment found; run skein experiment-assign first")
    m=json.loads(p.read_text(encoding="utf-8")); typer.echo(json.dumps({"experiment_id":load_config(root).experiment_id,"tasks":len(load_tasks(root)),"assignments":len(m.get("assignments",[])),"validation_errors":m.get("validation_errors",[]),"confounds":m.get("confounds",[]),"manifest_verified":verify_manifest(m)},indent=2))

@app.command("experiment-report")
def experiment_report_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Render the v0.6 experimental control-plane report."""
    from .experiment import RESULT_NAME, write_report
    root=path.resolve(); p=root/RESULT_NAME
    if not p.exists(): raise typer.BadParameter("No experiment assignment found; run skein experiment-assign first")
    m=json.loads(p.read_text(encoding="utf-8")); typer.echo(f"Experiment report written: {write_report(root,m)}")

@app.command("experiment-verify")
def experiment_verify_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Verify the reproducibility manifest has not been tampered with."""
    from .experiment import RESULT_NAME, verify_manifest
    p=path.resolve()/RESULT_NAME
    if not p.exists(): raise typer.BadParameter("No experiment manifest found")
    ok=verify_manifest(json.loads(p.read_text(encoding="utf-8"))); typer.echo(json.dumps({"verified":ok},indent=2));
    if not ok: raise typer.Exit(code=1)

@app.command("experiment-power")
def experiment_power_cmd(stddev:float=typer.Option(...,"--stddev"), effect:float=typer.Option(...,"--effect"), alpha:float=typer.Option(0.05,"--alpha"), power:float=typer.Option(0.80,"--power")):
    """Provide transparent paired-study sample-size planning guidance."""
    from .experiment import power_guidance
    typer.echo(json.dumps(power_guidance(stddev,effect,alpha,power),indent=2))

@app.command("experiment-package")
def experiment_package_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Create and checksum the reproducible v0.6 experiment evidence record."""
    from .experiment import RESULT_NAME, package_evidence
    root=path.resolve(); p=root/RESULT_NAME
    if not p.exists(): raise typer.BadParameter("No experiment manifest found; run skein experiment-assign first")
    typer.echo(json.dumps(package_evidence(root,json.loads(p.read_text(encoding="utf-8"))),indent=2))


@app.command("agent-adapter-list")
def agent_adapter_list_cmd():
    """List the built-in v0.7 agent adapter types."""
    from .agent_adapters import AnthropicAdapter, OpenAIAdapter, GenericSDKAdapter, CliAgentAdapter
    typer.echo(json.dumps({"schema_version": "0.7.0", "adapters": [
        {"name": "cli", "provider": CliAgentAdapter.provider},
        {"name": "openai", "provider": OpenAIAdapter.provider},
        {"name": "anthropic", "provider": AnthropicAdapter.provider},
        {"name": "generic-sdk", "provider": GenericSDKAdapter.provider},
    ]}, indent=2))

@app.command("agent-run")
def agent_run_cmd(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    task_id: str = typer.Option(..., "--task-id"),
    arm: str = typer.Option(..., "--arm", help="Must match the randomized experiment assignment."),
    command_json: str = typer.Option(..., "--command-json", help="JSON argv array; never interpreted by a shell."),
    context_query: str | None = typer.Option(None, "--context-query"),
    timeout: float = typer.Option(300.0, "--timeout"),
    agent: str = typer.Option("cli-agent", "--agent"),
):
    """Execute one assigned agent task with Baseline or Skein context and capture telemetry."""
    from .agent_runtime import ExecutionRequest, execute
    try:
        command = json.loads(command_json)
        if not isinstance(command, list):
            raise ValueError("--command-json must decode to a JSON array")
        record = execute(path.resolve(), ExecutionRequest(task_id=task_id, arm=arm, command=tuple(command), context_query=context_query, timeout_seconds=timeout, agent=agent))
    except (ValueError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(record.to_dict(), indent=2))
    if record.outcome != "success":
        raise typer.Exit(code=1)

@app.command("agent-status")
def agent_status_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)):
    """Show v0.7 controlled agent execution totals."""
    from .agent_runtime import execution_summary
    typer.echo(json.dumps(execution_summary(path.resolve()), indent=2))



@app.command("context-select")
def context_select_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), task_id:str=typer.Option(...,"--task-id"), query_text:str=typer.Option(...,"--query"), budget:int=typer.Option(1200,"--budget")):
    """Select minimal, relevant graph context using Adaptive Context Intelligence."""
    from .context_intelligence import AdaptiveContextEngine
    engine=AdaptiveContextEngine(path,budget_tokens=budget)
    selection=engine.select(task_id,query_text)
    typer.echo(json.dumps(selection.to_dict(),indent=2))

@app.command("context-render")
def context_render_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), task_id:str=typer.Option(...,"--task-id"), query_text:str=typer.Option(...,"--query"), budget:int=typer.Option(1200,"--budget")):
    """Render the adaptive context envelope for an agent."""
    from .context_intelligence import AdaptiveContextEngine
    engine=AdaptiveContextEngine(path,budget_tokens=budget)
    typer.echo(engine.render(engine.select(task_id,query_text)))

@app.command("context-feedback")
def context_feedback_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False), selection_id:str=typer.Option(...,"--selection-id"), node_id:str=typer.Option(...,"--node"), reward:float=typer.Option(...,"--reward"), task_id:str=typer.Option("","--task-id"), reason:str=typer.Option("","--reason")):
    """Record relevance feedback used by future adaptive selections."""
    from .context_intelligence import AdaptiveContextEngine
    event=AdaptiveContextEngine(path).feedback_event(selection_id,node_id,reward,task_id=task_id,reason=reason)
    typer.echo(json.dumps(event.to_dict(),indent=2))

@app.command("context-health")
def context_health_cmd(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    """Show Adaptive Context Intelligence learning health."""
    from .context_intelligence import context_health
    typer.echo(json.dumps(context_health(path),indent=2))

@app.command("quality-loop")
def quality_loop_cmd(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    task_id: str = typer.Option(..., "--task-id"),
    task_description: str = typer.Option(..., "--task"),
    command_json: str = typer.Option(..., "--command-json", help="JSON argv array; no shell interpretation."),
    agent: str = typer.Option("quality-loop-agent", "--agent"),
    max_iterations: int = typer.Option(3, "--max-iterations"),
    budget: int = typer.Option(1200, "--budget"),
):
    """Run the bounded v0.9 autonomous quality loop with the controlled CLI agent."""
    from .agent_adapters import CliAgentAdapter
    from .agent_runtime import execute
    from .autonomous_loop import run_quality_loop
    try:
        command = json.loads(command_json)
        if not isinstance(command, list) or any(not isinstance(x, str) or not x for x in command):
            raise ValueError("--command-json must decode to a non-empty JSON argv array")
        adapter = CliAgentAdapter(lambda request: execute(path.resolve(), ExecutionRequest(task_id=request.task_id, arm="skein", command=tuple(command), agent=request.agent)))
        result = run_quality_loop(path.resolve(), task_id=task_id, task_description=task_description, adapter=adapter, agent=agent, max_iterations=max_iterations, budget_tokens=budget)
    except (ValueError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(result.to_dict(), indent=2))
    if not result.passed:
        raise typer.Exit(code=1)

@app.command("quality-loop-status")
def quality_loop_status_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)):
    """Show v0.9 autonomous quality-loop totals."""
    from .autonomous_loop import quality_loop_summary
    typer.echo(json.dumps(quality_loop_summary(path.resolve()), indent=2))

@app.command("control-init")
def control_init_cmd(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    task_id: str = typer.Option(..., "--task-id"),
    title: str = typer.Option(..., "--title"),
    description: str = typer.Option(..., "--description"),
    spec: list[str] = typer.Option([], "--spec"),
    risk: str = typer.Option("medium", "--risk"),
    approval: bool = typer.Option(True, "--approval/--no-approval"),
    actor: str = typer.Option("local-admin", "--actor"),
):
    """Create a governed v1.0 AI-DLC control-plane run."""
    from .control_plane import ControlPlane, ControlTask
    if risk not in {"low", "medium", "high", "critical"}:
        raise typer.BadParameter("risk must be low, medium, high, or critical")
    run = ControlPlane(path).create(ControlTask(task_id, title, description, tuple(spec), risk, approval), actor=actor)
    typer.echo(json.dumps(run.to_dict(), indent=2))

@app.command("control-plan")
def control_plan_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False), actor: str = typer.Option("local-admin", "--actor")):
    """Admit the current task into the governed execution plan."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).plan(actor=actor).to_dict(), indent=2))

@app.command("control-begin")
def control_begin_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False), selection_id: str | None = typer.Option(None, "--selection-id"), actor: str = typer.Option("local-admin", "--actor")):
    """Begin the controlled execution phase."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).begin_execution(actor=actor, selection_id=selection_id).to_dict(), indent=2))

@app.command("control-evaluate")
def control_evaluate_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False), passed: bool = typer.Option(..., "--passed/--failed"), score: float = typer.Option(..., "--score"), execution_id: str | None = typer.Option(None, "--execution-id"), actor: str = typer.Option("quality-gate", "--actor")):
    """Record objective engineering-quality evidence."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).record_evaluation(passed=passed, score=score, execution_id=execution_id, actor=actor).to_dict(), indent=2))

@app.command("control-approve")
def control_approve_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False), actor: str = typer.Option(..., "--actor"), reason: str = typer.Option(..., "--reason")):
    """Record an explicit human approval."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).approve(actor=actor, reason=reason).to_dict(), indent=2))

@app.command("control-finalize")
def control_finalize_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False), actor: str = typer.Option("control-plane", "--actor")):
    """Finalize an approved AI-DLC run."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).finalize(actor=actor).to_dict(), indent=2))

@app.command("control-reject")
def control_reject_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False), actor: str = typer.Option(..., "--actor"), reason: str = typer.Option(..., "--reason")):
    """Reject the active run with an auditable reason."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).reject(actor=actor, reason=reason).to_dict(), indent=2))

@app.command("control-status")
def control_status_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)):
    """Show the active AI-DLC control-plane state."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).status(), indent=2))

@app.command("control-export")
def control_export_cmd(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)):
    """Export the active run and its immutable event evidence."""
    from .control_plane import ControlPlane
    typer.echo(json.dumps(ControlPlane(path).export(), indent=2))

if __name__ == "__main__":
    app()
