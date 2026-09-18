"""Opt-in deterministic Docker verification; no real provider account or paid calls."""
import os
import sys
from pathlib import Path
import pytest
pytest.importorskip('openai')
pytest.importorskip('mcp')
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from examples.agent_workflow.stack import execute

pytestmark=pytest.mark.skipif(os.environ.get('TD_AGENT_WORKFLOW_E2E')!='1',reason='Set TD_AGENT_WORKFLOW_E2E=1 for isolated Docker workflow')


def test_two_agents_model_to_mcp():
  report=execute('synthetic-model')
  assert report['downstream_reads']==2 and report['downstream_deletes']==0
  assert report['revoked_keys_denied'] and report['expired_fixture_keys_denied']
  assert {e['reason'] for e in report['blocked_decisions']}=={'tool_not_allowed_for_agent','local_policy_denied'}
