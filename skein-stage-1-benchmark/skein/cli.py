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
from .benchmarks import raw_context, graph_context, tokens, run_suite

app=typer.Typer(help="Skein — the continuous thread of AI-DLC.")
@app.command()
def version(): typer.echo(f"skein {__version__} | graph schema {SCHEMA_VERSION}")
@app.command()
def init(path:Path=typer.Argument(Path("."),exists=True,file_okay=False)):
    d=path/".skein"; d.mkdir(exist_ok=True)
    (d/"graph.json").write_text('{\n  "schema_version": "1.0.0",\n  "nodes": [],\n  "edges": []\n}\n')
    (d/"manifest.json").write_text('{"version":1,"files":{}}\n')
    typer.echo(f"Initialized Skein workspace: {d}")
@app.command()
def ingest(path:Path=typer.Argument(Path("."),exists=True,file_okay=False),full_rebuild:bool=False):
    d=path/".skein"; d.mkdir(exist_ok=True); gp=d/"graph.json"; store=LocalGraphStore.load(gp) if gp.exists() else LocalGraphStore()
    r=IncrementalIngester(path,store).ingest(full_rebuild=full_rebuild); store.save(gp)
    typer.echo(f"Ingestion complete: +{r.added_files} added, {r.changed_files} changed, {r.unchanged_files} unchanged, -{r.removed_files} removed; {r.nodes} nodes, {r.edges} edges")
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

if __name__=="__main__": app()
