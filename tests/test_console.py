"""Standalone Community console boundaries, without private packages or SDK."""
import importlib.util
import pytest
pytest.importorskip('psutil')
from fastapi.testclient import TestClient
from asr_proxy.console.app import create_app
from asr_proxy.console.runtime import Runtime
from asr_proxy.console.network import NetworkConfig, NetworkManager
from asr_proxy.console.scenarios import CASES
from asr_proxy.console.store import Store

HEADERS={'origin':'http://127.0.0.1:5176','x-td-demo':'1'}


def test_public_dependency_and_capability_boundary(tmp_path):
  assert importlib.util.find_spec('trapdefense_enterprise') is None
  assert importlib.util.find_spec('asr') is None
  with TestClient(create_app(tmp_path,seed=False)) as c:
    assert c.get('/demo-api/network').status_code==401
    c.headers.update(HEADERS)
    assert c.post('/demo-api/login',json={'username':'admin','password':'1234'}).status_code==200
    view=c.get('/demo-api/overview').json()
    assert view['edition']=='community' and view['capabilities']['broker'] is False
    assert all(case['id'] not in ('deploy','unknown') for case in view['scenarios'])
    assert c.post('/demo-api/approvals/fake/approve',json={'comment':'No fake approvals'}).status_code==404
    assert c.post('/demo-api/network',headers={'origin':'https://invalid.test'},json={}).status_code==403
    assert c.post('/demo-api/network',json={'listen_address':'0.0.0.0'}).status_code==422


def test_password_policy_and_persistence(tmp_path):
  with TestClient(create_app(tmp_path,seed=False)) as c:
    c.headers.update(HEADERS)
    c.post('/demo-api/login',json={'username':'admin','password':'1234'}).raise_for_status()
    cookie=c.cookies.get('td_demo_session')
    policy=c.get('/demo-api/policy').json()
    assert policy['pii_rules']=={'notes.read':'inherit','notes.delete':'inherit'}
    policy['rules']['notes.read']='block'
    policy['pii_rules']['notes.read']='block'
    assert c.post('/demo-api/policy',json=policy).status_code==200
    assert c.post('/demo-api/policy',json=policy).status_code==400
    assert c.post('/demo-api/password',json={'current_password':'wrong','new_password':'Synthetic-5678'}).status_code==400
    assert c.post('/demo-api/password',json={'current_password':'1234','new_password':'Synthetic-5678'}).status_code==200
    assert c.get('/demo-api/overview').status_code==401
    assert c.post('/demo-api/login',json={'username':'admin','password':'1234'}).status_code==401
  with TestClient(create_app(tmp_path,seed=False)) as c:
    c.headers.update(HEADERS);c.cookies.set('td_demo_session',cookie)
    assert c.get('/demo-api/policy').status_code==401
    c.cookies.clear()  # Remove the intentionally injected revoked cookie before normal sign-in.
    assert c.post('/demo-api/login',json={'username':'admin','password':'Synthetic-5678'}).status_code==200
    saved=c.get('/demo-api/policy').json()
    assert saved['rules']['notes.read']=='block' and saved['pii_rules']['notes.read']=='block'


def test_network_rejects_unsafe_settings_and_stale_revision(tmp_path):
  for values in ({'topology':'bridge'},{'listen_address':'0.0.0.0'},{'listen_port':5176},{'listen_port':18081},{'max_body_bytes':1}):
    with pytest.raises(ValueError):NetworkConfig(**values)
  manager=NetworkManager(Store(tmp_path))
  before=manager.current()
  with pytest.raises(ValueError,match='refresh'):manager.apply({**before,'version':99})
  assert manager.current()==before


def test_stream_response_reuses_request_selected_pii_policy(tmp_path):
  from asr_proxy.console.dataplane import StreamInspection
  from asr_proxy.inspection.contracts import HttpMessage, Verdict
  runtime=Runtime(tmp_path)
  stream=StreamInspection(runtime)
  stream.verdict=Verdict('allow','policy_allowed','inline',
    pii_policy_action='block',pii_policy_scope='tool')
  message=HttpMessage('POST','tools.demo.test','/mcp',{'content-type':'application/json'},
    b'{"message":"alex@example.com"}')
  result=stream.inspect_response(message,mode='inline',pii_action='block',pii_policy_scope='tool')
  assert (result.action,result.reason,result.pii_policy_scope)==('block','pii_block_policy','tool')


def test_real_community_console_proxy(tmp_path):
  import asyncio
  import os
  import socket
  import httpx
  if os.environ.get('TD_CONSOLE_E2E')!='1':pytest.skip('Set TD_CONSOLE_E2E=1 to exercise the real Envoy container')
  async def exercise():
    runtime=Runtime(tmp_path)
    await runtime.start()
    async def run(name):return await asyncio.to_thread(runtime.run,name)
    try:
      allowed=await run('read')
      assert allowed['action']=='allow' and allowed['transport']['http_status']==200
      assert allowed['transport']['receipt']
      blocked=await run('delete')
      assert blocked['action']=='block' and blocked['transport']['http_status']==403
      assert blocked['transport']['upstream_received'] is False
      pii=await run('pii')
      assert pii['action']=='redact' and pii['transport']['receipt']['request_redacted']
      secret=await run('secret')
      assert secret['action']=='block' and secret['reason']=='secret_detected'
      assert secret['transport']['upstream_received'] is False
      assert CASES['secret']['message'] not in str(runtime.store.events())
      response=await run('response')
      assert response['action']=='redact' and response['transport']['response_redacted']
      assert 'alex@example.com' not in str(runtime.store.events())
      policy=runtime.policy();policy['mode']='mirror';policy['pii_rules']['notes.read']='block'
      await asyncio.to_thread(runtime.apply,policy)
      mirror_pii=await run('pii')
      assert mirror_pii['action']=='block' and mirror_pii['reason']=='pii_block_policy'
      assert mirror_pii['hypothetical_action']=='would_block' and not mirror_pii['enforcement_applied']
      assert mirror_pii['pii_policy_action']=='block' and mirror_pii['pii_policy_scope']=='tool'
      assert mirror_pii['transport']['http_status']==200 and mirror_pii['transport']['upstream_received']
      assert mirror_pii['transport']['receipt']['request_redacted'] is False
      policy=runtime.policy();policy['mode']='inline';policy['pii_rules']['notes.read']='inherit'
      await asyncio.to_thread(runtime.apply,policy)
      policy=runtime.policy();policy['rules']['notes.read']='block'
      await asyncio.to_thread(runtime.apply,policy)
      assert (await run('read'))['transport']['http_status']==403
      policy=runtime.policy();policy['mode']='mirror'
      await asyncio.to_thread(runtime.apply,policy)
      mirror=await run('delete')
      assert not mirror['enforcement_applied'] and mirror['transport']['receipt']
      settings=runtime.network.current();settings['listen_port']=18092
      await asyncio.to_thread(runtime.update_network,settings)
      assert (await run('read'))['transport']['http_status']==200
      current=runtime.network.current()
      with socket.socket() as occupied:
        occupied.bind(('127.0.0.1',18093));occupied.listen()
        with pytest.raises(ValueError):await asyncio.to_thread(runtime.update_network,{**current,'listen_port':18093})
      assert runtime.network.current()==current
      policy=runtime.policy();policy['mode']='inline';policy['rules']['notes.read']='allow'
      await asyncio.to_thread(runtime.apply,policy)
      async with httpx.AsyncClient(timeout=10,trust_env=False) as c:
        response=await c.post('http://127.0.0.1:18092/mcp',headers={'host':'tools.demo.test'},json={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'notes.read','arguments':{'message':'hello'}}})
        assert response.status_code==403
        count=len(runtime.destination.receipts)
        await asyncio.to_thread(runtime.workers.stop)
        response=await c.post('http://127.0.0.1:18092/mcp',json={})
        assert response.status_code>=500 and len(runtime.destination.receipts)==count
    finally:await runtime.stop()
  asyncio.run(exercise())


@pytest.mark.parametrize('terminal', ['response_body', 'response_headers', 'immediate_response'])
def test_evidence_committed_before_final_extproc_reply(tmp_path, monkeypatch, terminal):
  """A client may close the generator without requesting another response."""
  import asyncio
  from envoy.service.ext_proc.v3 import external_processor_pb2 as pb
  from asr_proxy.console import dataplane
  from asr_proxy.inspection.contracts import Verdict

  async def fake_process(processor, requests, context):
    async for _ in requests:pass
    processor.engine.verdict=Verdict('block' if terminal=='immediate_response' else 'allow','policy_allowed','inline')
    reply=pb.ProcessingResponse()
    getattr(reply,terminal).SetInParent()
    yield reply

  monkeypatch.setattr(dataplane.ExternalProcessor,'Process',fake_process)
  async def exercise():
    runtime=Runtime(tmp_path)
    async def requests():
      yield pb.ProcessingRequest(response_headers=pb.HttpHeaders(end_of_stream=terminal=='response_headers'))
    stream=dataplane.ConsoleProcessor(runtime).Process(requests(),None)
    result=await anext(stream)
    assert result.WhichOneof('response')==terminal
    events=runtime.store.events()
    assert len(events)==1 and events[0]['transport']['stream_completed'] is True
    await stream.aclose()
    assert len(runtime.store.events())==1
  asyncio.run(exercise())


def test_cancelled_partial_stream_keeps_incomplete_evidence(tmp_path, monkeypatch):
  import asyncio
  from envoy.service.ext_proc.v3 import external_processor_pb2 as pb
  from asr_proxy.console import dataplane
  from asr_proxy.inspection.contracts import Verdict

  async def partial_process(processor, requests, context):
    processor.engine.verdict=Verdict('allow','policy_allowed','inline')
    yield pb.ProcessingResponse(request_body=pb.BodyResponse())

  monkeypatch.setattr(dataplane.ExternalProcessor,'Process',partial_process)
  async def exercise():
    runtime=Runtime(tmp_path)
    stream=dataplane.ConsoleProcessor(runtime).Process(None,None)
    await anext(stream)
    assert runtime.store.events()==[]
    await stream.aclose()
    event,=runtime.store.events()
    assert event['action']=='unknown' and event['coverage']=='incomplete'
    assert not event['enforcement_applied'] and not event['transport']['stream_completed']
  asyncio.run(exercise())

def test_synthetic_receipt_id_cannot_look_like_personal_data(monkeypatch):
  from types import SimpleNamespace
  from asr_proxy.console import destination
  from asr_proxy.inspection.pii import PresidioScanner
  collision='d688a6576def415c96762d8aa2a7266a'
  scanner=PresidioScanner()
  assert scanner.analyze(collision)  # A random hex UUID can resemble a passport.
  monkeypatch.setattr(destination,'uuid4',lambda:SimpleNamespace(hex=collision))
  receipt=destination.receipt_id()
  assert len(receipt)==32 and receipt.isalpha()
  assert not scanner.analyze(receipt)
