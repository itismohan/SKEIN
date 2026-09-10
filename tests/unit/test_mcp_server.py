import json
from pathlib import Path
import pytest
from skein.mcp.server import call_tool, handle

def test_mcp_tools_list():
    r=handle({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}},Path('.'))
    names={x['name'] for x in r['result']['tools']}
    assert {'query_graph','get_subgraph','get_traceability','get_diff','propose_node','propose_edge'} <= names

def test_scoped_write_blocks_out_of_scope():
    with pytest.raises(PermissionError):
        call_tool('propose_node', {'role':'planner','node':{'id':'x','type':'Code-Change'}}, Path('.'))

def test_scoped_write_allows_planner():
    r=call_tool('propose_node', {'role':'planner','node':{'id':'x','type':'Plan'}}, Path('.'))
    assert r['status']=='proposed'

def test_identity_scope_blocks_commit_for_planner(tmp_path):
    (tmp_path/'.skein').mkdir()
    (tmp_path/'.skein'/'mcp-policy.json').write_text(json.dumps({'identities':{'p1':'planner'},'roles':{'planner':['read_graph','propose']}}))
    with pytest.raises(PermissionError):
        call_tool('commit_proposal', {'identity':'p1','proposal_id':'missing'}, tmp_path)

def test_mcp_tools_call_uses_transport_identity(tmp_path):
    (tmp_path/'.skein').mkdir()
    (tmp_path/'.skein'/'mcp-policy.json').write_text(json.dumps({'identities':{'planner-1':'planner'},'roles':{'planner':['read_graph','propose']}}))
    (tmp_path/'.skein'/'graph.json').write_text(json.dumps({'schema_version':'1.0.0','nodes':[],'edges':[]}))
    r=handle({'jsonrpc':'2.0','id':7,'method':'tools/call','params':{'name':'propose_node','identity':'planner-1','arguments':{'node':{'id':'p1','kind':'Plan'}}}},tmp_path)
    assert 'result' in r
    assert 'proposed' in r['result']['content'][0]['text']
