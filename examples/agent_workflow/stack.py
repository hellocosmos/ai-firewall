"""Two isolated Compose projects, owned temporary state and explicit synthetic/live mode."""
import asyncio
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
from uuid import uuid4
import httpx
import yaml
from asr_proxy.selfhost.config import Deployment
from .agent import run
from examples.mcp_pilot.client import session,text_content

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=Path(__file__).resolve().parent


def free_port():
  with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));return sock.getsockname()[1]


class Stack:
  def __init__(self,base,kind,model,live):
    self.directory=base/kind;self.directory.mkdir()
    self.evidence=self.directory/'evidence';self.evidence.mkdir(mode=0o777);self.evidence.chmod(0o777)
    self.kind,self.live=kind,live
    self.project='td042-'+kind+'-'+uuid4().hex[:8]
    self.port,self.gateway_port=free_port(),free_port()
    self.origin=f'http://127.0.0.1:{self.port}'
    self.url=f'http://127.0.0.1:{self.gateway_port}'
    common={'console_origin':self.origin,'gateway_auth':{'mode':'agent_key'},
      'access_broker':{'enabled':True,'tenant_id':'workflow'},
      'target_auth':{'mode':'static_bearer','secret_file':'/state/target-key'}}
    if kind=='model':config=Deployment.model_validate({**common,'llm':{'provider':'openai','models':[model]}})
    else:
      common.update(upstream='http://workflow-fixture:8080',allow_plaintext_upstream=True,routes=[{
        'authority':'workflow-fixture:8080','path':'/mcp','protocol':'mcp','tools':{
          name:{'action':action,'resource':resource,'effect':'block' if name=='notes_delete' else 'allow'}
          for name,action,resource in [('initialize','initialize','mcp'),('notifications/initialized','notify','mcp'),
            ('tools/list','discover','mcp'),('notes_read','read','notes'),('notes_delete','delete','notes')]},
        'redact_fields':['/params/arguments/message']}])
      config=Deployment.model_validate(common)
    path=self.directory/'deployment.yaml';path.write_text(yaml.safe_dump(config.model_dump(exclude_none=True)))
    self.env={**os.environ,'TD_CONFIG_FILE':str(path),'TD_CONSOLE_PORT':str(self.port),'TD_GATEWAY_PORT':str(self.gateway_port)}
    services={'app':{'volumes':[str(EXAMPLE/'bootstrap.py')+':/workflow/bootstrap.py:ro']}}
    if kind=='mcp' or not live:
      fixture={'image':'python:3.12-slim-bookworm','command':['python','/fixture/server.py'],
        'user':f'{os.getuid()}:{os.getgid()}',
        'volumes':[str(EXAMPLE/'fixture.py')+':/fixture/server.py:ro',str(self.evidence)+':/evidence'],
        'networks':{'egress':{'aliases':['api.openai.com'] if kind=='model' else []}}}
      if kind=='model':
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
          '-subj','/CN=api.openai.com','-addext','subjectAltName=DNS:api.openai.com',
          '-keyout',str(self.directory/'key.pem'),'-out',str(self.directory/'cert.pem')],
          check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        fixture['environment']={'FIXTURE_TLS':'1'}
        fixture['volumes'] += [str(self.directory/'key.pem')+':/fixture/key.pem:ro',str(self.directory/'cert.pem')+':/fixture/cert.pem:ro']
        services['envoy']={'volumes':[str(self.directory/'cert.pem')+':/etc/ssl/certs/ca-certificates.crt:ro']}
      services['workflow-fixture']=fixture
    override=self.directory/'compose.yaml';override.write_text(yaml.safe_dump({'services':services}))
    self.command=['docker','compose','-p',self.project,'-f',str(ROOT/'deploy/selfhost/compose.yaml'),'-f',str(override)]

  def compose(self,*args,input=None,timeout=300):
    result=subprocess.run([*self.command,*args],env=self.env,cwd=ROOT,input=input,text=True,capture_output=True,timeout=timeout)
    if result.returncode:
      # Never print bootstrap stdout, stdin, target credentials or raw provider responses.
      raise RuntimeError('Docker command failed: '+args[0]+'; '+result.stderr[-1500:])
    return result.stdout

  def initialize(self,target):
    self.credentials=json.loads(self.compose('run','--rm','--no-deps','-T','--entrypoint','python','app','/workflow/bootstrap.py',
      input=json.dumps({'password':secrets.token_urlsafe(24),'target_key':target})))
    self.compose('up','-d')

  def ready(self):
    until=time.monotonic()+40
    while time.monotonic()<until:
      try:
        if httpx.get(self.origin+'/demo-api/health',timeout=2).status_code==200:
          # Envoy listener/DNS may lag console health. Probe only a side-effect-free MCP initialize
          # for the MCP stack; model readiness is established by the bounded SDK request.
          if self.kind=='model':return
          r=httpx.post(self.url+'/mcp',headers={'authorization':'Bearer '+self.key('agent-a')},json={
            'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},
            'clientInfo':{'name':'readiness','version':'0.42'}}},timeout=5)
          if r.status_code==200:return
      except httpx.HTTPError:pass
      time.sleep(.5)
    raise RuntimeError('Gateway readiness failed: '+self.kind)

  def key(self,agent):return self.credentials[agent]['credential']

  def receipts(self):
    path=self.evidence/'receipts.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

  def decisions(self):
    code="from asr_proxy.console.store import Store; import json; print(json.dumps([{**{k:e.get(k) for k in ('agent','tool','action','reason')},'upstream_received':e.get('transport',{}).get('upstream_received')} for e in Store('/state',require_existing=True).events()]))"
    return json.loads(self.compose('exec','-T','app','python','-c',code))

  def revoke_active_agent(self):
    code="from asr_proxy.selfhost.config import load; from asr_proxy.selfhost.runtime import SelfhostRuntime; from asr_proxy.selfhost.agent_credentials import AgentCredentials; import json,sys; runtime=SelfhostRuntime('/state',load('/config/deployment.yaml')); keys=AgentCredentials('/state/agent-credentials.sqlite',runtime.broker,'workflow'); keys.revoke('agent-a',json.load(sys.stdin)['id'])"
    self.compose('exec','-T','app','python','-c',code,input=json.dumps({'id':self.credentials['agent-a']['credential_id']}))

  def cleanup(self):
    self.compose('down','-v','--remove-orphans',timeout=90)


async def verify(model,mcp,name,live):
  outcomes={}
  if not live:
    response=httpx.post(model.url+'/v1/chat/completions',headers={'Authorization':'Bearer '+model.key('agent-a')},
      json={'model':name,'messages':[{'role':'user','content':'Synthetic header boundary probe'}]},timeout=20)
    assert response.status_code==200 and 'set-cookie' not in response.headers,'LLM response cookies were forwarded'
    assert response.json()['created']==1779123456,'Protocol timestamp was changed'
    response=httpx.post(model.url+'/v1/chat/completions',headers={'Authorization':'Bearer '+model.key('agent-a')},
      json={'model':name,'messages':[{'role':'user','content':'Synthetic SSE boundary probe'}],'stream':True},timeout=20)
    assert response.status_code==200 and response.headers.get('content-type','').startswith('text/event-stream')
    text=''.join(choice.get('delta',{}).get('content','') for line in response.text.splitlines()
      if line.startswith('data: {') for choice in json.loads(line[6:]).get('choices',[]))
    assert text=='*'*len('alex@example.com') and 'data: [DONE]' in response.text,'Split SSE PII escaped inspection'

  for agent,task in [('agent-a','read'),('agent-b','read'),('agent-a','delete')]:
    result=await run(model.url+'/v1',model.key(agent),name,mcp.url+'/mcp',mcp.key(agent),task)
    expected='notes_read' if task=='read' else 'notes_delete'
    assert result['status']=='finished' and result['turns']>=2, 'Model did not complete the required tool cycle'
    assert len(result['calls'])==1 and result['calls'][0]['tool']==expected,'Required tool was not exercised'
    expected_ok=agent=='agent-a' and task=='read'
    assert result['calls'][0]['succeeded']==expected_ok,'Unexpected tool permission outcome'
    if expected_ok:assert result['calls'][0]['pii_absent'] and result['calls'][0]['redacted'],'Response PII was not redacted'
    outcomes[agent+'-'+task]=result
  # Request redaction independently exercised even if a live model uses no PII arguments.
  async with session(mcp.url+'/mcp',mcp.key('agent-a')) as client:
    result=await client.call_tool('notes_read',{'message':'contact alex@example.com'})
    assert not result.isError and 'alex@example.com' not in text_content(result)
  # Revoked/expired keys are checked on both enforcement points, with no target execution.
  for stack in (model,mcp):
    stack.revoke_active_agent()
    for kind in ('agent-a','revoked','expired'):
      response=httpx.post(stack.url+('/v1/chat/completions' if stack.kind=='model' else '/mcp'),
        headers={'Authorization':'Bearer '+stack.key(kind)},json={},timeout=10)
      assert response.status_code==401, 'Invalid agent key admitted'
  decisions=mcp.decisions()
  for agent,tool,reason in [('agent-b','notes_read','tool_not_allowed_for_agent'),('agent-a','notes_delete','local_policy_denied')]:
    assert any(e['agent']==agent and e['tool']==tool and e['action']=='block' and e['reason']==reason
      and e['upstream_received'] is False for e in decisions),'Expected enforced decision evidence missing'
  receipts=mcp.receipts()
  assert sum(r['kind']=='notes_read' for r in receipts)==2,'Unexpected downstream read count'
  assert not any(r['kind']=='notes_delete' or r['pii_received'] for r in receipts),'Denied action or raw PII reached tool'
  if not live:
    assert sum(r['kind']=='model_tool_result' for r in model.receipts())==3
    assert not any(r['pii_received'] for r in model.receipts()),'Raw tool PII reached synthetic model'
  return {'evidence':'live_openai_with_synthetic_mcp' if live else 'scripted_model_with_real_sdk_gateway_envoy_mcp',
    'model':name,'scenarios':outcomes,'downstream_reads':2,'downstream_deletes':0,
    'blocked_decisions':[e for e in decisions if e['action']=='block'],
    'revoked_keys_denied':True,'expired_fixture_keys_denied':True,
    'limits':'Synthetic business data; bounded text/function calls. Expiry is a seeded past timestamp. Buffered SSE checked only in synthetic mode. No realtime streaming, immediate cancellation or production capacity claim.'}


def execute(model_name,provider_key_file=None):
  live=provider_key_file is not None
  key='synthetic-target-only'
  if live:
    path=Path(provider_key_file)
    if not path.is_file() or path.stat().st_mode&0o077:raise ValueError('Use an owner-only provider key file (0600)')
    key=path.read_text().strip()
    if not key or any(c.isspace() for c in key):raise ValueError('Invalid provider key file')
  with tempfile.TemporaryDirectory(prefix='td042-') as temporary:
    stacks=[]
    try:
      model=Stack(Path(temporary),'model',model_name,live);stacks.append(model)
      mcp=Stack(Path(temporary),'mcp',model_name,live);stacks.append(mcp)
      print('Building the existing self-hosted image...',flush=True)
      model.compose('build','app',timeout=600)
      for stack in stacks:
        print('Starting isolated '+stack.kind+' gateway...',flush=True)
        stack.initialize(key if stack.kind=='model' else 'synthetic-target-only');stack.ready()
      print('Verifying two-agent model → MCP → model workflows...',flush=True)
      return asyncio.run(verify(model,mcp,model_name,live))
    finally:
      cleanup_errors=[]
      for stack in reversed(stacks):
        try:stack.cleanup()
        except Exception:cleanup_errors.append(stack.project)
      if cleanup_errors:print('Cleanup required for owned projects: '+', '.join(cleanup_errors),flush=True)
      if cleanup_errors:raise RuntimeError('Owned test projects need cleanup: '+', '.join(cleanup_errors))
