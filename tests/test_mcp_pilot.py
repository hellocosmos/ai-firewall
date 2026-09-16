"""Optional example boundary checks, no Docker or model required."""
import sys
from pathlib import Path
import json
import pytest
pytest.importorskip('mcp')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi.testclient import TestClient
from examples.mcp_pilot.adapter import create_app
from examples.mcp_pilot.server import Documents
from asr_proxy.inspection.identity import AttestationVerifier
from asr_proxy.inspection.contracts import HttpMessage


def test_documents_are_real_but_finite(tmp_path):
  store = Documents(tmp_path/'docs.sqlite')
  store.call('write_document','draft','Approved update')
  assert store.call('read_document','draft') == 'Approved update'
  with pytest.raises(ValueError):store.call('read_document','../../etc/passwd')
  store.call('delete_document','protected')
  with pytest.raises(ValueError):store.call('read_document','protected')


def test_adapter_preserves_body_removes_forgery_and_signs(tmp_path):
  captured=[];key=b'k'*48;token='t'*40
  def receive(request):
    captured.append(request)
    identity=AttestationVerifier(key,str(tmp_path/'nonces.sqlite'),required_fields=('source_id',)).verify(
      HttpMessage('POST','pilot.test','/mcp',dict(request.headers),request.content),consume=True)
    assert identity['source_id']=='pilot-adapter'
    return httpx.Response(202)
  app=create_app('http://127.0.0.1:23456','pilot.test',key,token,transport=httpx.MockTransport(receive))
  raw=b'{ "jsonrpc": "2.0", "method": "notifications/initialized" }'
  with TestClient(app) as client:
    assert client.post('/mcp',content=raw).status_code==401
    response=client.post('/mcp',content=raw,headers={'Authorization':'Bearer '+token,
      'Content-Type':'application/json','X-TD-Attestation':'forged','X-Forwarded-For':'forged'})
    assert response.status_code==202
    assert len(captured)==1 and captured[0].content==raw
    assert 'authorization' not in captured[0].headers and 'x-forwarded-for' not in captured[0].headers
    assert client.post('/mcp',content=b'x'*65537,headers={'Authorization':'Bearer '+token,
      'Content-Type':'application/json'}).status_code==413
    assert len(captured)==1


@pytest.mark.parametrize('endpoint',['https://example.com','http://127.0.0.1:10/elsewhere','http://localhost:80'])
def test_adapter_rejects_nonfixed_targets(endpoint):
  with pytest.raises(ValueError):create_app(endpoint,'pilot.test',b'k'*48,'t'*40)


def test_adapter_rejects_duplicate_auth_and_unsupported_encoding():
  captured=[]
  def receive(request):captured.append(request);return httpx.Response(200,content=b'ok')
  app=create_app('http://127.0.0.1:23456','pilot.test',b'k'*48,'t'*40,transport=httpx.MockTransport(receive))
  with TestClient(app) as client:
    headers=[('authorization','Bearer '+'t'*40),('authorization','Bearer '+'t'*40),('content-type','application/json')]
    assert client.post('/mcp',content=b'{}',headers=headers).status_code==400
    headers={'authorization':'Bearer '+'t'*40,'content-type':'application/json','content-encoding':'gzip'}
    assert client.post('/mcp',content=b'{}',headers=headers).status_code==400
  assert captured==[]


def test_adapter_bounds_response_without_redirect_retry():
  captured=[]
  def receive(request):captured.append(request);return httpx.Response(200,content=b'x'*65537)
  app=create_app('http://127.0.0.1:23456','pilot.test',b'k'*48,'t'*40,transport=httpx.MockTransport(receive))
  with TestClient(app) as client:
    assert client.post('/mcp',json={},headers={'authorization':'Bearer '+'t'*40}).status_code==502
  assert len(captured)==1


def test_model_endpoint_is_explicit_local_only():
  from examples.mcp_pilot.agent import model_endpoint
  assert model_endpoint('http://127.0.0.1:11439/v1')=='http://127.0.0.1:11439/v1/chat/completions'
  for url in ['https://provider.example/v1','http://localhost:11434/v1','http://127.0.0.1:10/v1?key=example']:
    with pytest.raises(ValueError):model_endpoint(url)


@pytest.mark.asyncio
async def test_model_loop_reports_failure_without_scripted_fallback(monkeypatch):
  from contextlib import asynccontextmanager
  from types import SimpleNamespace
  from examples.mcp_pilot import agent
  class Client:
    async def list_tools(self):return SimpleNamespace(tools=[])
  @asynccontextmanager
  async def fake_session(*args):yield Client()
  async def failure(*args):raise ValueError('private model payload')
  monkeypatch.setattr(agent,'session',fake_session)
  monkeypatch.setattr(agent,'completion',failure)
  result=await agent.run_agent('http://unused',None,'http://127.0.0.1:11439/v1','test-model')
  assert result['status']=='model_error' and result['calls']==[]
  assert 'private model payload' not in str(result)


@pytest.mark.asyncio
async def test_model_arguments_are_schema_validated_before_mcp(monkeypatch):
  from contextlib import asynccontextmanager
  from types import SimpleNamespace
  from examples.mcp_pilot import agent
  class Client:
    async def list_tools(self):
      return SimpleNamespace(tools=[SimpleNamespace(name='read_document',description='Read',
        inputSchema={'type':'object','properties':{'document_id':{'type':'string'}},'required':['document_id']})])
  @asynccontextmanager
  async def fake_session(*args):yield Client()
  async def malformed(*args):
    return {'tool_calls':[{'id':'a','function':{'name':'read_document','arguments':'{"document_id": []}'}}]}
  async def forbidden(*args):raise AssertionError('Invalid arguments reached MCP')
  monkeypatch.setattr(agent,'session',fake_session);monkeypatch.setattr(agent,'completion',malformed)
  monkeypatch.setattr(agent,'invoke',forbidden)
  result=await agent.run_agent('unused',None,'http://127.0.0.1:11439/v1','test-model')
  assert result['status']=='invalid_tool_calls' and result['calls']==[]
