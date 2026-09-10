from __future__ import annotations
import re
from .store import LocalGraphStore

def query(store:LocalGraphStore, text:str)->str:
    m=re.search(r"what calls (.+?)[?]*$",text,re.I)
    if m:
        needle=m.group(1).strip().strip('"\'')
        matches=[]
        for n,d in store.graph.nodes(data=True):
            if needle in n or needle == d.get("attributes",{}).get("name") or needle == d.get("attributes",{}).get("qualified_name"):
                matches.append(n)
        lines=[f"Matches for: {needle}"]
        for target in matches:
            callers=[u for u,v,d in store.graph.in_edges(target,data=True) if d.get("type")=="CALLS"]
            lines.extend([f"  <- {c} ({next(iter(store.graph.get_edge_data(c, target).values())).get('attributes',{}).get('confidence','UNKNOWN')})" for c in callers])
        return "\n".join(lines)
    return "Supported query: what calls <node>"
