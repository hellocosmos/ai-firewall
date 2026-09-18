"""Initialize disposable example state. Input/output travels through private pipes."""
import json
import sys
import time
from pathlib import Path
from asr_proxy.selfhost.main import initialize
from asr_proxy.selfhost.config import load
from asr_proxy.selfhost.runtime import SelfhostRuntime
from asr_proxy.selfhost.agent_credentials import AgentCredentials
from asr_proxy.access_broker import AgentRecord
from asr_proxy.inspection.pool import atomic_write


def main():
  data=json.load(sys.stdin)
  config=load('/config/deployment.yaml')
  initialize(Path('/state'),Path('/generated'),config,data['password'])
  atomic_write(Path('/state/target-key'),data['target_key'])
  runtime=SelfhostRuntime('/state',config)
  is_model=config.llm is not None
  keys=AgentCredentials('/state/agent-credentials.sqlite',runtime.broker,'workflow')
  result={}
  for agent in ('agent-a','agent-b'):
    tools=['llm.chat'] if is_model else ['initialize','notifications/initialized','tools/list']+(['notes_read','notes_delete'] if agent=='agent-a' else [])
    runtime.broker.register_agent(AgentRecord(agent_id=agent,tenant_id='workflow',owner_id='synthetic-operator',
      allowed_tools=tools,allowed_resources=config.llm.models if is_model else ['mcp','notes'],
      allowed_actions=['invoke'] if is_model else ['initialize','notify','discover','read','delete'],allow_autonomous=True))
    result[agent]=keys.issue(agent)
  revoked=keys.issue('agent-a');keys.revoke('agent-a',revoked['credential_id']);result['revoked']=revoked
  expired=keys.issue('agent-a',60)
  # Deterministic expired credential fixture, not a wall-clock duration measurement.
  with keys.connect() as db:db.execute('UPDATE credentials SET expires=? WHERE id=?',(time.time()-1,expired['credential_id']))
  result['expired']=expired
  print(json.dumps(result))


if __name__=='__main__':main()
