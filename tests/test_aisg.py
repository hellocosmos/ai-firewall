"""AISG agent credentials and autonomous authorization security boundaries."""
from pathlib import Path
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from fastapi.testclient import TestClient
from asr_proxy.access_broker import AccessBroker, AgentRecord, AccessRequest, ApprovalDecisionRequest, FileAccessBrokerStore
from asr_proxy.selfhost.agent_credentials import AgentCredentials
from asr_proxy.selfhost.auth import GatewayAuthenticator, AuthError
from asr_proxy.selfhost.config import AgentKeyGatewayAuth, Deployment, load
from asr_proxy.selfhost.gateway import create_gateway
from asr_proxy.inspection.identity import AttestationVerifier
from asr_proxy.inspection.contracts import HttpMessage


def setup(tmp_path):
  broker=AccessBroker(FileAccessBrokerStore(tmp_path/'broker.json'))
  broker.register_agent(AgentRecord(agent_id='agent-a',tenant_id='tenant-a',owner_id='owner',
    allow_autonomous=True,allowed_tools=['notes.read','notes.delete'],allowed_resources=['notes'],allowed_actions=['read','delete']))
  keys=AgentCredentials(tmp_path/'keys.sqlite',broker,'tenant-a')
  request=AccessRequest(authorization_mode='agent',tenant_id='tenant-a',agent_id='agent-a',
    tool_name='notes.read',resource_id='notes',requested_action='read',metadata={'request_digest':'a'*64})
  return broker,keys,request


def test_autonomous_scopes_and_default_deny(tmp_path):
  broker,keys,request=setup(tmp_path)
  assert broker.authorize(request).action=='allow'
  for update,reason in [({'tenant_id':'other'},'agent_tenant_mismatch'),
      ({'requested_action':'export'},'action_not_allowed_for_agent'),
      ({'user_id':'spoofed'},'mixed_authorization_context'),
      ({'authorization_mode':'delegated'},'delegation_context_required')]:
    assert broker.authorize(request.model_copy(update=update)).reason_code==reason
  agent=broker.store.get_agent('agent-a')
  broker.register_agent(agent.model_copy(update={'allow_autonomous':False}))
  assert broker.authorize(request).reason_code=='autonomous_not_allowed'


def test_autonomous_approval_bound_once_and_mirror_read_only(tmp_path):
  broker,keys,request=setup(tmp_path)
  request=request.model_copy(update={'requested_action':'delete','tool_name':'notes.delete'})
  before=broker.store.path.read_bytes()
  assert broker.evaluate(request).action=='approval_required'
  assert broker.store.path.read_bytes()==before
  decision=broker.authorize(request)
  assert decision.approval.authorization_mode=='agent'
  broker.approve(decision.approval.approval_id,ApprovalDecisionRequest(approver_id='admin'))
  approved=request.model_copy(update={'approval_id':decision.approval.approval_id})
  assert broker.authorize(approved.model_copy(update={'metadata':{'request_digest':'b'*64}})).reason_code=='approval_context_mismatch'
  with ThreadPoolExecutor(max_workers=2) as pool:
    outcomes=list(pool.map(broker.authorize,[approved,approved]))
  assert sorted(d.action for d in outcomes)==['allow','block']
  assert broker.authorize(approved).reason_code=='approval_consumed'


def test_local_credential_lifecycle_and_tenant_isolation(tmp_path):
  broker,keys,_=setup(tmp_path)
  issued=keys.issue('agent-a',60)
  token=issued['credential']
  assert token.encode() not in keys.path.read_bytes()
  assert 'digest' not in json.dumps(keys.list('agent-a'))
  assert AgentCredentials(keys.path,broker,'other').authenticate(token) is None
  assert keys.authenticate(token)['agent_id']=='agent-a'
  with pytest.raises(ValueError):keys.issue('agent-a',60,rotate_id='missing')
  assert keys.authenticate(token)
  rotated=keys.issue('agent-a',60,rotate_id=issued['credential_id'])
  assert keys.authenticate(token) is None
  assert keys.authenticate(rotated['credential'])
  keys.revoke('agent-a',rotated['credential_id'])
  assert keys.authenticate(rotated['credential']) is None
  expiring=keys.issue('agent-a',60)
  with keys.connect() as db:db.execute('UPDATE credentials SET expires=0 WHERE id=?',(expiring['credential_id'],))
  assert keys.authenticate(expiring['credential']) is None
  active=keys.issue('agent-a',60)
  broker.register_agent(broker.store.get_agent('agent-a').model_copy(update={'enabled':False}))
  assert keys.authenticate(active['credential']) is None
  assert keys.path.stat().st_mode & 0o077 == 0


def test_gateway_strips_local_key_and_binds_only_verified_identity(tmp_path):
  broker,keys,_=setup(tmp_path)
  key=keys.issue('agent-a')['credential']
  auth=GatewayAuthenticator(AgentKeyGatewayAuth(),client_key='',agent_credentials=keys)
  base=load(Path(__file__).parents[1]/'deploy/selfhost/deployment.yaml').model_dump(exclude_none=True)
  base.update(gateway_auth={'mode':'agent_key'},access_broker={'enabled':True,'tenant_id':'tenant-a'},target_auth={'mode':'none'})
  config=Deployment.model_validate(base)
  sign=b'x'*32
  seen=[]
  def target(request):
    assert 'authorization' not in request.headers
    assert 'x-td-agent-id' not in request.headers
    message=HttpMessage('POST','fixture:8080','/api/notes',dict(request.headers),request.content)
    identity=AttestationVerifier(sign,str(tmp_path/'nonce.sqlite'),required_fields=('tenant_id','agent_id')).verify(message,consume=True)
    assert identity['agent_id']=='agent-a' and identity['authorization_mode']=='agent'
    assert identity['approval_id']=='apv_'+'a'*12
    seen.append(True)
    class Body(httpx.AsyncByteStream):
      async def __aiter__(self):yield b'{"ok":true}'
    return httpx.Response(200,stream=Body(),headers={'content-type':'application/json'})
  with TestClient(create_gateway(config,'',sign,authenticator=auth,transport=httpx.MockTransport(target))) as client:
    assert client.post('/api/notes',json={}).status_code==401
    response=client.post('/api/notes',json={},headers={'Authorization':'Bearer '+key,
      'X-TD-Agent-ID':'forged','X-TD-Approval-ID':'apv_'+'a'*12})
    assert response.status_code==200
    keys.revoke('agent-a',keys.list('agent-a')[0]['credential_id'])
    assert client.post('/api/notes',json={},headers={'Authorization':'Bearer '+key}).status_code==401
  assert len(seen)==1


def test_console_credential_api_and_no_secret_in_audit(tmp_path):
  from asr_proxy.console.app import create_app
  app=create_app(tmp_path,seed=False)
  with TestClient(app) as client:
    client.headers.update({'origin':'http://127.0.0.1:5176','x-td-demo':'1'})
    assert client.post('/demo-api/agents/local-agent/credentials',json={}).status_code==401
    client.post('/demo-api/login',json={'username':'admin','password':'1234'}).raise_for_status()
    client.post('/demo-api/agents',json={'agent_id':'local-agent','owner_id':'team',
      'allowed_tools':['notes.read'],'allow_autonomous':True}).raise_for_status()
    result=client.post('/demo-api/agents/local-agent/credentials',json={'ttl_seconds':60})
    result.raise_for_status()
    token=result.json()['credential']
    assert token not in client.get('/demo-api/audit').text
    assert token not in client.get('/demo-api/agents/local-agent/credentials').text
    client.post('/demo-api/agents/local-agent/status',json={'enabled':False}).raise_for_status()
    assert client.post('/demo-api/agents/local-agent/credentials',json={}).status_code==400


def test_viewer_cannot_manage_agent_credentials(tmp_path):
  from asr_proxy.console.app import create_app
  app=create_app(tmp_path,seed=False)
  with TestClient(app) as client:
    token=app.state.runtime.store.create_session({'username':'viewer','role':'viewer','authentication':'local'})
    client.cookies.set('td_demo_session',token)
    client.headers.update({'origin':'http://127.0.0.1:5176','x-td-demo':'1'})
    for path,payload in [('/agents/a/credentials',{}),('/agents/a/credentials/key_a/revoke',{}),('/agents/a/status',{'enabled':False})]:
      assert client.post('/demo-api'+path,json=payload).status_code==403
