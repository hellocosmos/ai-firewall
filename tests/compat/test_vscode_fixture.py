"""The generated workspace stays loopback-only and uses synthetic credentials."""
import json

from .vscode_fixture import CLIENT_KEY,prepare_workspace


def test_prepare_workspace(tmp_path):
  workspace=tmp_path/'workspace'
  prepare_workspace(workspace,19184)
  config=json.loads((workspace/'.vscode/mcp.json').read_text())
  server=config['servers']['trapdefense-compat']
  assert server=={
    'type':'http','url':'http://127.0.0.1:19184/mcp',
    'headers':{'X-TD-Client-Key':CLIENT_KEY},
  }
  assert 'loopback-only' in (workspace/'README.md').read_text()
