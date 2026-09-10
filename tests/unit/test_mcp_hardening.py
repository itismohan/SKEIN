import json
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

from skein.mcp.server import call_tool, handle


def workspace(tmp: Path):
    (tmp / '.skein' / 'history').mkdir(parents=True)
    (tmp / '.skein' / 'graph.json').write_text(
        json.dumps({'schema_version': '1.0.0', 'nodes': [], 'edges': []}), encoding='utf-8'
    )
    (tmp / 'spec' / 'clauses').mkdir(parents=True)
    import shutil
    src = Path(__file__).parents[2] / 'spec' / 'clauses'
    shutil.copytree(src, tmp / 'spec' / 'clauses', dirs_exist_ok=True)


def test_write_requires_identity():
    with TemporaryDirectory() as td:
        root = Path(td); workspace(root)
        with pytest.raises(PermissionError, match='authenticated identity'):
            call_tool('propose_node', {'node': {'id': 'x', 'kind': 'Plan'}}, root)


def test_unknown_tool_is_jsonrpc_method_error():
    with TemporaryDirectory() as td:
        root = Path(td); workspace(root)
        result = handle({'jsonrpc': '2.0', 'id': 7, 'method': 'tools/nope'}, root)
        assert result['error']['code'] == -32601


def test_notification_has_no_response():
    with TemporaryDirectory() as td:
        root = Path(td); workspace(root)
        assert handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, root) == {}


def test_tools_call_invalid_arguments_is_invalid_params():
    with TemporaryDirectory() as td:
        root = Path(td); workspace(root)
        result = handle({'jsonrpc': '2.0', 'id': 8, 'method': 'tools/call', 'params': {'name': 'query_graph', 'arguments': []}}, root)
        assert result['error']['code'] == -32602


def test_http_write_cannot_use_caller_supplied_role():
    from skein.mcp.http import create_app
    from fastapi.testclient import TestClient
    with TemporaryDirectory() as td:
        root = Path(td); workspace(root)
        client = TestClient(create_app(root))
        result = client.post('/mcp', json={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'propose_node','role':'admin','arguments':{'node':{'id':'x','kind':'Plan'}}}})
        assert result.json()['error']['code'] == -32000


def test_proposal_commit_is_not_replayable():
    with TemporaryDirectory() as td:
        root = Path(td); workspace(root)
        proposed = call_tool('propose_node', {'identity':'local-admin','node':{'id':'x','kind':'Plan'}}, root)
        first = call_tool('commit_proposal', {'identity':'local-admin','proposal_id':proposed['proposal_id']}, root)
        from pytest import raises
        with raises(KeyError):
            call_tool('commit_proposal', {'identity':'local-admin','proposal_id':proposed['proposal_id']}, root)
        assert first['status'] == 'committed'
