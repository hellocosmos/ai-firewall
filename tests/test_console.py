"""Standalone Community console boundaries, without private packages or SDK."""
import importlib.util
import pytest
pytest.importorskip('psutil')
from fastapi.testclient import TestClient
from asr_proxy.console.app import create_app
from asr_proxy.console.runtime import Runtime
from asr_proxy.console.network import NetworkConfig, NetworkManager
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
    policy['rules']['notes.read']='block'
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
    assert c.get('/demo-api/policy').json()['rules']['notes.read']=='block'


def test_network_rejects_unsafe_settings_and_stale_revision(tmp_path):
  for values in ({'topology':'bridge'},{'listen_address':'0.0.0.0'},{'listen_port':5176},{'listen_port':18081},{'max_body_bytes':1}):
    with pytest.raises(ValueError):NetworkConfig(**values)
  manager=NetworkManager(Store(tmp_path))
  before=manager.current()
  with pytest.raises(ValueError,match='refresh'):manager.apply({**before,'version':99})
  assert manager.current()==before


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
      response=await run('response')
      assert response['action']=='redact' and response['transport']['response_redacted']
      assert 'alex@example.com' not in str(runtime.store.events())
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
        await runtime.grpc_server.stop(0);runtime.inspector_ready=False
        response=await c.post('http://127.0.0.1:18092/mcp',json={})
        assert response.status_code>=500 and len(runtime.destination.receipts)==count
    finally:await runtime.stop()
  asyncio.run(exercise())
