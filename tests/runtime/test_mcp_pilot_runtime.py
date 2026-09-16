"""Real optional SDK-to-Envoy-to-MCP regression with document effects."""
import asyncio
import os
from pathlib import Path
import sys
import pytest
pytest.importorskip('mcp')
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from examples.mcp_pilot.harness import Pilot
from examples.mcp_pilot.verify import run_suite, verify_outage
pytestmark=pytest.mark.skipif(os.environ.get('TD_MCP_PILOT')!='1',reason='opt-in real MCP pilot')


def test_real_mcp_lifecycle_controls_and_outage(tmp_path):
  async def exercise():
    with Pilot(tmp_path/'pilot') as pilot:
      report=await run_suite(pilot,samples=5)
      assert all(case['passed'] for case in report['cases'])
      assert any(case.get('known_detection_miss') for case in report['cases'])
      assert (await verify_outage(pilot))['downstream_executions']==0
  asyncio.run(exercise())
