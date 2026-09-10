from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path
from dataclasses import dataclass
import networkx as nx
from .parsers import ParserRegistry
from .documents import DocumentExtractor
from .links import ticket_adr_links
from .models import ParsedNode, ParsedEdge
from ..schema import GraphNode, GraphEdge, NodeType, EdgeType
from ..store import LocalGraphStore

TEXT_DOCS={".md",".markdown",".txt",".rst",".pdf"}
CODE_IGNORES={".git",".skein","node_modules","dist","build","__pycache__",".venv","venv"}

@dataclass
class IngestionReport:
    added_files:int=0; changed_files:int=0; unchanged_files:int=0; removed_files:int=0; nodes:int=0; edges:int=0

class IncrementalIngester:
    def __init__(self, root: Path, store: LocalGraphStore, registry: ParserRegistry|None=None):
        self.root=root.resolve(); self.store=store; self.registry=registry or ParserRegistry(); self.docs=DocumentExtractor()
        self.manifest_path=self.root/".skein"/"manifest.json"
        self.manifest=self._load_manifest()
    def _load_manifest(self):
        if self.manifest_path.exists(): return json.loads(self.manifest_path.read_text())
        return {"version":1,"files":{}}
    def _save_manifest(self):
        self.manifest_path.parent.mkdir(parents=True,exist_ok=True); self.manifest_path.write_text(json.dumps(self.manifest,indent=2)+"\n")
    def _hash(self,p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
    def _files(self):
        for p in self.root.rglob("*"):
            if not p.is_file() or any(part in CODE_IGNORES for part in p.parts): continue
            if self.registry.for_path(p) or p.suffix.lower() in TEXT_DOCS: yield p
    def _to_graph(self, nodes:list[ParsedNode], edges:list[ParsedEdge]):
        for n in nodes:
            try: self.store.add_node(GraphNode(id=n.id,type=n.type,attributes=n.attributes))
            except Exception: pass
        for e in edges:
            if not self.store.graph.has_node(e.source): self.store.add_node(GraphNode(id=e.source,type="File",attributes={"placeholder":True}))
            if not self.store.graph.has_node(e.target): self.store.add_node(GraphNode(id=e.target,type="File",attributes={"placeholder":True}))
            etype = e.type if e.type in {x.value for x in EdgeType} else "INFERRED"
            attrs={**e.attributes,"confidence":e.confidence}
            self.store.add_edge(GraphEdge(source=e.source,target=e.target,type=etype,attributes=attrs))

    def _resolve_symbol_calls(self) -> None:
        """Resolve cross-file CALLS placeholders using exact extracted function names."""
        by_name = {}
        for node, data in self.store.graph.nodes(data=True):
            if data.get("type") == "Function":
                name = data.get("attributes", {}).get("name")
                if name:
                    by_name.setdefault(name, []).append(node)
        replacements = []
        for source, target, key, data in list(self.store.graph.edges(keys=True, data=True)):
            if data.get("type") != "CALLS" or not str(target).startswith("symbol:"):
                continue
            symbol = str(target)[7:]
            candidates = by_name.get(symbol, [])
            if len(candidates) != 1:
                continue
            replacements.append((source, target, key, candidates[0], data))
        for source, target, key, resolved, data in replacements:
            self.store.graph.remove_edge(source, target, key=key)
            attrs = dict(data.get("attributes", {}))
            attrs["resolved_from"] = target
            attrs["confidence"] = "INFERRED"
            self.store.graph.add_edge(source, resolved, type="CALLS", attributes=attrs)
    def ingest(self, full_rebuild=False)->IngestionReport:
        report=IngestionReport(); current={}
        files=list(self._files())
        for p in files:
            rel=p.relative_to(self.root).as_posix(); h=self._hash(p); current[rel]=h
            old=self.manifest["files"].get(rel)
            if old==h and not full_rebuild: report.unchanged_files+=1; continue
            report.changed_files += 1 if old else 0; report.added_files += 0 if old else 1
            source=p.read_text(encoding="utf-8",errors="ignore") if p.suffix.lower()!=".pdf" else ""
            parser=self.registry.for_path(p)
            if parser: parsed=parser.parse(p,source)
            else: parsed=self.docs.extract(p,source)
            self._remove_file_region(rel)
            self._to_graph(parsed.nodes,parsed.edges)
            self._to_graph([],ticket_adr_links(p,source,set(self.store.graph.nodes)))
        for rel in set(self.manifest["files"])-set(current):
            self._remove_file_region(rel); report.removed_files+=1
        self._resolve_symbol_calls()
        self.manifest["files"]=current; self._save_manifest()
        doc=self.store.to_document(); report.nodes=len(doc.nodes); report.edges=len(doc.edges)
        return report
    def _remove_file_region(self, rel:str):
        prefixes=(f"file:{rel}",f"function:{rel}:",f"class:{rel}:",f"document:{rel}")
        doomed=[n for n in self.store.graph.nodes if n.startswith(prefixes)]
        self.store.graph.remove_nodes_from(doomed)
        # Remove module edges that are owned by this file.
        fid=f"file:{rel}"
        if fid in self.store.graph: self.store.graph.remove_edges_from(list(self.store.graph.out_edges(fid,keys=True)))

    def community_hierarchy(self):
        g=nx.Graph(); g.add_nodes_from(self.store.graph.nodes)
        for u,v,d in self.store.graph.edges(data=True):
            if d.get("type") in ("CALLS","IMPORTS"): g.add_edge(u,v)
        if not g.edges: return []
        communities=list(nx.community.greedy_modularity_communities(g))
        return [{"id":f"community:{i+1}","size":len(c),"nodes":sorted(c)} for i,c in enumerate(communities)]
