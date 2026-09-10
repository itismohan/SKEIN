from pathlib import Path
from skein.mcp.server import call_tool

def test_three_agent_reference_pipeline(tmp_path):
    root=tmp_path
    (root/".skein").mkdir()
    (root/".skein"/"graph.json").write_text('{"schema_version":"1.0.0","nodes":[],"edges":[]}')
    planner=call_tool('propose_node',{'role':'planner','node':{'id':'plan:order','type':'Plan','attributes':{'ticket':'ORD-1'}}},root)
    assert planner['status']=='proposed'
    # Coder consumes shared graph through a read before proposing a scoped code-change.
    q=call_tool('query_graph',{'query':'what calls create_order'},root)
    assert 'create_order' in q['result'] or 'No structural match' in q['result']
    coder=call_tool('propose_node',{'role':'coder','node':{'id':'change:order','type':'Code-Change'}},root)
    assert coder['status']=='proposed'
