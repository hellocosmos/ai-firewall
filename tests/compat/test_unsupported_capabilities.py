"""Executable evidence for capabilities the 0.38 profile does not claim."""
from pathlib import Path

from fastapi.testclient import TestClient
import httpx
import pytest

from asr_proxy.selfhost.config import load
from asr_proxy.selfhost.gateway import create_gateway


ROOT=Path(__file__).parents[2]
CLIENT_KEY='synthetic-client-'+'x'*32
SIGNING_KEY=b'synthetic-signing-key-'+b'x'*32


def gateway(transport):
  config=load(ROOT/'deploy/selfhost/deployment.yaml')
  return TestClient(create_gateway(config,CLIENT_KEY,SIGNING_KEY,transport=transport))


def test_stateful_mcp_methods_and_inbound_session_fail_before_forward():
  calls=[]
  client=gateway(httpx.MockTransport(lambda request:calls.append(request)))
  headers={'x-td-client-key':CLIENT_KEY}
  assert client.get('/mcp',headers=headers).status_code==403
  assert client.delete('/mcp',headers=headers).status_code==403
  response=client.post('/mcp',headers={**headers,'mcp-session-id':'synthetic-session'},json={
    'jsonrpc':'2.0','id':1,'method':'tools/list'})
  assert response.status_code==400
  assert response.json()=={'error':'unsupported_session_or_upgrade'}
  assert calls==[]


@pytest.mark.parametrize(('headers','error'),[
  ({'content-type':'text/event-stream'},'streaming_not_supported'),
  ({'content-type':'application/json','mcp-session-id':'synthetic-session'},
   'upstream_session_not_supported'),
])
def test_upstream_stream_or_session_fails_closed(headers,error):
  def target(request):
    return httpx.Response(200,headers=headers,stream=httpx.ByteStream(b'{}'))
  client=gateway(httpx.MockTransport(target))
  response=client.post('/mcp',headers={'x-td-client-key':CLIENT_KEY},json={
    'jsonrpc':'2.0','id':1,'method':'tools/list'})
  assert response.status_code==502 and response.json()=={'error':error}
