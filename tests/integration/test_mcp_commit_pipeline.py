from pathlib import Path
import shutil, json
from skein.mcp.server import call_tool

def test_reviewer_commit_is_sdd_governed(tmp_path):
    root=tmp_path; (root/'.skein').mkdir(); (root/'spec'/'clauses').mkdir(parents=True)
    (root/'.skein'/'graph.json').write_text(json.dumps({'schema_version':'1.0.0','nodes':[],'edges':[]}))
    shutil.copy('spec/clauses/SKN-007-shared-agent-protocol.yaml', root/'spec'/'clauses')
    p=call_tool('propose_node',{'role':'planner','node':{'id':'plan:1','type':'File','kind':'Plan'}},root)
    r=call_tool('commit_proposal',{'role':'reviewer','proposal_id':p['proposal_id'],'spec_refs':['SKN-007']},root)
    assert r['status']=='committed'
    assert (root/'.skein'/'history'/'commits.jsonl').exists()
