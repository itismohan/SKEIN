from __future__ import annotations
import json, sys, hashlib
from pathlib import Path
from typing import Any
from ..store import LocalGraphStore
from ..versioning import VersionedGraphStore, diff_graphs
from ..query import query as graph_query
from ..sdd.traceability import TraceabilityStore
from ..schema import GraphDocument, GraphNode, GraphEdge, NodeType, EdgeType
from ..telemetry import TelemetryStore
from ..governance.policy import load_policy

TOOLS = {
 'query_graph': {'description':'Query the shared Skein graph','inputSchema':{'type':'object','properties':{'query':{'type':'string'}}}},
 'get_subgraph': {'description':'Get a node neighborhood','inputSchema':{'type':'object','properties':{'node_id':{'type':'string'},'hops':{'type':'integer'}}}},
 'get_traceability': {'description':'Get traceability links for a spec or commit','inputSchema':{'type':'object','properties':{'spec_ref':{'type':'string'},'commit_id':{'type':'string'}}}},
 'get_diff': {'description':'Get structural diff from a graph version','inputSchema':{'type':'object','properties':{'from_commit':{'type':'string'},'to_commit':{'type':'string'}}}},
 'propose_node': {'description':'Propose a graph node subject to identity scope','inputSchema':{'type':'object','required':['node'],'properties':{'identity':{'type':'string'},'node':{'type':'object'}}}},
 'commit_proposal': {'description':'Commit an approved proposal through the SDD pipeline','inputSchema':{'type':'object','required':['proposal_id'],'properties':{'identity':{'type':'string'},'proposal_id':{'type':'string'},'spec_refs':{'type':'array','items':{'type':'string'}}}}},
 'propose_edge': {'description':'Propose a graph edge subject to identity scope','inputSchema':{'type':'object','required':['edge'],'properties':{'identity':{'type':'string'},'edge':{'type':'object'}}}},
}

ROLE_ALLOWED={'planner':{'Plan'},'coder':{'Code-Change'},'reviewer':{'Review'},'tester':{'Test'},'admin':{'Plan','Code-Change','Review','Test'}}

def _proposal_path(root: Path): return _workspace(root)/'history'/'proposals.jsonl'

def _append_proposal(root: Path, record: dict):
    p=_proposal_path(root); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf-8') as f: f.write(json.dumps(record,sort_keys=True)+'\n')

def _proposals(root: Path):
    p=_proposal_path(root)
    if not p.exists(): return []
    latest: dict[str, dict] = {}
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            record = json.loads(line)
            latest[record['proposal_id']] = record
    return list(latest.values())


def _workspace(root: Path):
    return root/'.skein'

def call_tool(name: str, args: dict[str,Any], root: Path) -> dict[str,Any]:
    identity = args.get('identity')
    write_tools = {'propose_node', 'propose_edge', 'commit_proposal'}
    if name in write_tools and not identity and not args.get('role'):
        raise PermissionError('authenticated identity is required for write operations')
    policy = load_policy(_workspace(root) / 'mcp-policy.json')
    if identity:
        action = 'read_graph' if name in ('query_graph','get_subgraph') else 'read_trace' if name in ('get_traceability','get_diff') else 'propose' if name in ('propose_node','propose_edge') else 'commit' if name == 'commit_proposal' else None
        if action and not policy.allowed(identity, action):
            raise PermissionError(f'identity {identity!r} is not authorized for {action}')
        args = dict(args)
        args['role'] = policy.role_for(identity)
    telemetry = TelemetryStore(_workspace(root) / 'history')
    stage = args.get('lifecycle_stage') or {'query_graph':'design','get_subgraph':'design','get_traceability':'review','get_diff':'review','propose_node':'code','propose_edge':'code','commit_proposal':'review'}.get(name,'design')
    repo = str(root.resolve())
    team = str(args.get('team','default'))
    agent = str(identity or args.get('role','unknown'))
    try:
        result = _call_tool_impl(name, args, root)
        telemetry.log(repo=repo, team=team, agent=agent, lifecycle_stage=stage, operation=name, input_tokens=int(args.get('input_tokens',0)), output_tokens=int(args.get('output_tokens',0)), reasoning_tokens=args.get('reasoning_tokens'), estimated_cost_usd=args.get('estimated_cost_usd'))
        return result
    except Exception:
        telemetry.log(repo=repo, team=team, agent=agent, lifecycle_stage=stage, operation=name, input_tokens=int(args.get('input_tokens',0)), output_tokens=int(args.get('output_tokens',0)), reasoning_tokens=args.get('reasoning_tokens'), estimated_cost_usd=args.get('estimated_cost_usd'), outcome='error')
        raise

def _call_tool_impl(name: str, args: dict[str,Any], root: Path) -> dict[str,Any]:
    if name=='query_graph':
        store=LocalGraphStore.load(_workspace(root)/'graph.json'); return {'result':graph_query(store,args['query'])}
    if name=='get_subgraph':
        store=LocalGraphStore.load(_workspace(root)/'graph.json'); nid=args['node_id']; hops=int(args.get('hops',1)); seen={nid}; frontier={nid}
        for _ in range(hops):
            nxt=set()
            for u,v in store.graph.edges:
                if u in frontier: nxt.add(v)
                if v in frontier: nxt.add(u)
            frontier=nxt-seen; seen|=frontier
        nodes=[n for n in store.graph.nodes if n['id'] in seen]
        edges=[e for e in store.graph.edges if e['source'] in seen and e['target'] in seen]
        return {'nodes':nodes,'edges':edges}
    if name=='get_traceability':
        t=TraceabilityStore(_workspace(root)/'history')
        links=t.for_spec(args['spec_ref']) if args.get('spec_ref') else t.for_commit(args['commit_id']) if args.get('commit_id') else t.links()
        return {'links':[x.__dict__ for x in links]}
    if name=='get_diff':
        s=VersionedGraphStore(_workspace(root)/'history'); before=s.state_at(args['from_commit']); after=s.graph if not args.get('to_commit') else s.state_at(args['to_commit']); return {'diff':diff_graphs(before,after)}
    if name in ('propose_node','propose_edge'):
        role=args.get('role',''); allowed=ROLE_ALLOWED.get(role,set()); obj=args.get('node' if name=='propose_node' else 'edge',{})
        kind=obj.get('kind') or obj.get('type')
        if kind not in allowed:
            raise PermissionError(f'{role} cannot propose {kind}; allowed={sorted(allowed)}')
        proposal_id='proposal-'+hashlib.sha256(json.dumps({'role':role,'object':obj},sort_keys=True).encode()).hexdigest()[:16]
        rec={'proposal_id':proposal_id,'role':role,'kind':kind,'object':obj,'status':'proposed'}
        _append_proposal(root,rec)
        return rec
    if name=='commit_proposal':
        if args.get('role') not in {'reviewer','admin'}: raise PermissionError('only reviewer or admin may commit a proposal')
        proposal=next((p for p in _proposals(root) if p['proposal_id']==args['proposal_id'] and p['status']=='proposed'),None)
        if proposal is None: raise KeyError(f'unknown or already committed proposal: {args["proposal_id"]}')
        obj=proposal['object']; role=proposal['role']; kind=proposal['kind']
        history=_workspace(root)/'history'; store=VersionedGraphStore(history)
        graph=store.graph.model_copy(deep=True)
        if name=='commit_proposal':
            if 'node' in obj or 'id' in obj:
                node_type={'Plan':NodeType.FILE,'Code-Change':NodeType.FILE,'Review':NodeType.FILE,'Test':NodeType.TEST_CASE}[kind]
                attrs=dict(obj.get('attributes',{})); attrs['proposal_kind']=kind; attrs['proposed_by']=role
                node=GraphNode(id=obj['id'],type=node_type,attributes=attrs)
                graph.nodes=[n for n in graph.nodes if n.id!=node.id]+[node]
            elif 'source' in obj and 'target' in obj:
                edge=GraphEdge.model_validate(obj); graph.edges=[e for e in graph.edges if (e.source,e.target,e.type)==(edge.source,edge.target,edge.type)]+[edge]
            else: raise ValueError('proposal object must describe a node or edge')
        from ..sdd.commit_pipeline import SDDCommitPipeline
        specs=tuple(args.get('spec_refs') or ('SKN-007',))
        commit=SDDCommitPipeline(store, root/'spec'/'clauses').commit(graph,author=f'agent:{role}',message=f'commit proposal {args["proposal_id"]}',spec_refs=specs,expected_parent=store.head)
        rec=dict(proposal); rec['status']='committed'; rec['commit_id']=commit.commit_id; _append_proposal(root,rec)
        return {'status':'committed','commit_id':commit.commit_id}
    raise KeyError(name)

def handle(req:dict[str,Any], root:Path)->dict[str,Any]:
    try:
        method=req.get('method'); rid=req.get('id')
        if method=='initialize':
            result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'skein','version':'0.3.0'}}
        elif method=='notifications/initialized':
            return {}
        elif method=='tools/list':
            result={'tools':[{'name':n,**v} for n,v in TOOLS.items()]}
        elif method=='tools/call':
            p=req.get('params',{})
            if not isinstance(p, dict) or not p.get('name') or not isinstance(p.get('arguments',{}), dict):
                return {'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':'tools/call requires name and object arguments'}}
            arguments=dict(p.get('arguments',{}));
            if p.get('identity') and 'identity' not in arguments: arguments['identity']=p['identity']
            result={'content':[{'type':'text','text':json.dumps(call_tool(p['name'],arguments,root),default=str)}]}
        else:
            return {'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':f'unknown method: {method}'}}
        return {'jsonrpc':'2.0','id':rid,'result':result}
    except Exception as e:
        return {'jsonrpc':'2.0','id':req.get('id'),'error':{'code':-32000,'message':str(e)}}

def serve_stdio(root:Path):
    for line in sys.stdin:
        if line.strip(): print(json.dumps(handle(json.loads(line),root)),flush=True)
