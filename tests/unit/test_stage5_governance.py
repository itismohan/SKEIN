import json
from pathlib import Path
from skein.telemetry import TelemetryStore
from skein.compression.telemetry import CompressionTelemetry
from skein.dashboard import render
from skein.audit import generate
from skein.governance.policy import load_policy
from skein.governance.sandbox import SandboxPolicy, SandboxViolation


def test_telemetry_aggregation(tmp_path):
    store=TelemetryStore(tmp_path)
    store.log(repo='r',team='q',agent='a',lifecycle_stage='design',operation='query_graph',input_tokens=10,output_tokens=5,estimated_cost_usd=.01)
    assert store.aggregate()['by_stage']['design']['input_tokens']==10


def test_compression_health(tmp_path):
    t=CompressionTelemetry(tmp_path)
    t.record(outcome='pass',original_tokens=10,compressed_tokens=5,checklist_items=1)
    t.record(outcome='fallback',original_tokens=10,compressed_tokens=10,checklist_items=1)
    assert t.health()['fallback_rate']==.5


def test_dashboard_and_audit_render(tmp_path):
    (tmp_path/'.skein'/'history').mkdir(parents=True)
    assert 'Skein Governance Dashboard' in render(tmp_path)
    assert 'Skein Audit Report' in generate(tmp_path)


def test_identity_policy_and_sandbox(tmp_path):
    p=tmp_path/'policy.json'; p.write_text(json.dumps({'identities':{'alice':'reviewer'},'roles':{'reviewer':['commit']}}))
    policy=load_policy(p)
    assert policy.allowed('alice','commit')
    sandbox=SandboxPolicy(tmp_path)
    try:
        sandbox.check_path(tmp_path.parent/'outside.txt')
        assert False
    except SandboxViolation:
        pass
