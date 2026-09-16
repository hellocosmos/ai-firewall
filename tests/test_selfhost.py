"""Self-hosted trust boundaries; all credentials and targets are synthetic."""
import json
from pathlib import Path
import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from asr_proxy.selfhost.config import Deployment, load, envoy_config
from asr_proxy.selfhost.gateway import create_gateway
from asr_proxy.selfhost.main import initialize
from asr_proxy.console.store import Store
from asr_proxy.inspection.contracts import HttpMessage
from asr_proxy.inspection.identity import AttestationVerifier

KEY='synthetic-client-'+'x'*32
SIGN=b'synthetic-signing-key-'+b'x'*32

@pytest.fixture
def config():return load(Path(__file__).parents[1]/'deploy/selfhost/deployment.yaml')

@pytest.mark.parametrize('update',[
 {'upstream':'https://user:secret@example.com'}, {'upstream':'https://example.com/path'},
 {'upstream':'http://fixture:8080','allow_plaintext_upstream':False},
 {'console_origin':'https://example.com/path'}, {'destination_auth':'static_bearer'},
 {'bearer_file':'/secret'}, {'upstream':'https://127.0.0.1'},
])
def test_invalid_contract(config,update):
  with pytest.raises(ValueError):Deployment.model_validate({**config.model_dump(),**update})

def test_tls_and_private_inspector(config):
  data=config.model_dump();data['upstream']='https://api.example.com'
  for route in data['routes']:route['authority']='api.example.com'
  rendered=yaml.safe_load(envoy_config(Deployment.model_validate(data)))
  clusters=rendered['static_resources']['clusters']
  tls=clusters[1]['transport_socket']['typed_config']
  assert tls['sni']=='api.example.com'
  assert tls['common_tls_context']['validation_context']['match_typed_subject_alt_names'][0]['matcher']['exact']=='api.example.com'
  assert clusters[0]['load_assignment']['endpoints'][0]['lb_endpoints'][0]['endpoint']['address']['socket_address']['address']=='app'

def test_initialization_preserves_account(tmp_path,config):
  state=tmp_path/'state';generated=tmp_path/'generated'
  initialize(state,generated,config,'synthetic-password-036')
  store=Store(state,require_existing=True)
  assert store.check_password('synthetic-password-036') and not store.check_password('1234')
  assert store.changed()
  before=(state/'attestation.key').read_bytes()
  with pytest.raises(ValueError):initialize(state,generated,config,'another-password')
  assert (state/'attestation.key').read_bytes()==before
  assert (state/'client.key').stat().st_mode & 0o077 == 0
  with pytest.raises(ValueError):Store(tmp_path/'empty',require_existing=True)

def test_gateway_signs_actual_request_and_separates_auth(config,tmp_path):
  calls=[]
  def upstream(request):
    calls.append(request)
    message=HttpMessage(request.method,request.headers['host'],request.url.raw_path.decode(),dict(request.headers),request.content)
    verifier=AttestationVerifier(SIGN,str(tmp_path/'nonces'),required_fields=('source_id',))
    assert verifier.verify(message,consume=True)['source_id']=='selfhost-adapter'
    assert request.headers['authorization']=='Bearer synthetic-service-token'
    assert request.headers['x-api-key']=='synthetic-api-key'
    assert 'x-td-client-key' not in request.headers
    assert 'x-forwarded-for' not in request.headers
    return httpx.Response(200,headers={'content-type':'application/json'},stream=httpx.ByteStream(b'{}'))
  app=create_gateway(config,KEY,SIGN,transport=httpx.MockTransport(upstream))
  with TestClient(app) as client:
    result=client.post('/api/notes?q=hello',headers={'x-td-client-key':KEY,'authorization':'Bearer synthetic-service-token','x-api-key':'synthetic-api-key','x-forwarded-for':'spoofed'},json={'message':'safe'})
  assert result.status_code==200 and len(calls)==1
  assert calls[0].url.host=='envoy'

@pytest.mark.parametrize('headers,path,status',[
 ({},'/api/notes',401), ({'x-td-client-key':'bad'},'/api/notes',401),
 ({'x-td-client-key':KEY},'/unknown',403),
 ({'x-td-client-key':KEY,'cookie':'session=x'},'/api/notes',400),
 ({'x-td-client-key':KEY,'mcp-session-id':'session'},'/api/notes',400),
 ({'x-td-client-key':KEY,'content-encoding':'gzip'},'/api/notes',415),
 ({'x-td-client-key':KEY,'connection':'authorization'},'/api/notes',400),
])
def test_gateway_rejects_before_forward(config,headers,path,status):
  def forbidden(request):raise AssertionError('Must not reach Envoy')
  app=create_gateway(config,KEY,SIGN,transport=httpx.MockTransport(forbidden))
  assert TestClient(app).post(path,headers=headers,json={}).status_code==status

def test_static_bearer_and_conflict(config):
  seen=[]
  def target(request):
    seen.append(request.headers['authorization'])
    return httpx.Response(200,stream=httpx.ByteStream(b'{}'))
  client=TestClient(create_gateway(config,KEY,SIGN,bearer='synthetic-static',transport=httpx.MockTransport(target)))
  assert client.post('/api/notes',headers={'x-td-client-key':KEY},json={}).status_code==200
  assert seen==['Bearer synthetic-static']
  assert client.post('/api/notes',headers={'x-td-client-key':KEY,'authorization':'Bearer other'},json={}).status_code==400
  assert len(seen)==1

@pytest.mark.parametrize('status,headers,content,expected',[
 (302,{'location':'https://example.com'},b'',502),
 (200,{'content-type':'text/event-stream'},b'data: hello',502),
 (200,{'set-cookie':'session=x'},b'{}',502),
 (200,{'mcp-session-id':'x'},b'{}',502),
 (200,{},b'x'*1048577,502),
 (401,{'www-authenticate':'Bearer realm="target"'},b'{}',401),
],ids=['redirect','sse','cookie','session','large','unauthorized'])
def test_response_contract(config,status,headers,content,expected):
  transport=httpx.MockTransport(lambda request:httpx.Response(status,headers=headers,stream=httpx.ByteStream(content)))
  client=TestClient(create_gateway(config,KEY,SIGN,transport=transport))
  response=client.post('/api/notes',headers={'x-td-client-key':KEY},json={})
  assert response.status_code==expected
  assert 'www-authenticate' not in response.headers

def test_no_fallback(config):
  def unavailable(request):raise httpx.ConnectError('synthetic connection failure')
  client=TestClient(create_gateway(config,KEY,SIGN,transport=httpx.MockTransport(unavailable)))
  assert client.post('/api/notes',headers={'x-td-client-key':KEY},json={}).status_code==503

def test_body_limit(config):
  def forbidden(request):raise AssertionError('Must not forward large body')
  client=TestClient(create_gateway(config,KEY,SIGN,transport=httpx.MockTransport(forbidden)))
  assert client.post('/api/notes',headers={'x-td-client-key':KEY},content=b'x'*1048577).status_code==413
