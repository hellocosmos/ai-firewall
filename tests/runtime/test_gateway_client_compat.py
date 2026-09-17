"""Protocol-realistic synthetic compatibility checks for supported gateway clients."""
import json
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest

pytest.importorskip('mcp')
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from asr_proxy.selfhost.config import load
from asr_proxy.selfhost.gateway import create_gateway


ROOT=Path(__file__).parents[2]
CLIENT_KEY='synthetic-client-'+'x'*32
SIGNING_KEY=b'synthetic-signing-key-'+b'x'*32


def synthetic_target(calls):
  def handle(request):
    calls.append(request)
    assert request.headers.get('x-td-client-key') is None
    assert request.headers.get('x-td-attestation')
    payload=json.loads(request.content)
    if request.url.path=='/api/notes':
      body={'received':payload}
    elif payload['method']=='initialize':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{
        'protocolVersion':'2025-11-25','capabilities':{},
        'serverInfo':{'name':'synthetic-trapdefense-target','version':'0.38'}}}
    elif payload['method']=='tools/list':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{'tools':[
        {'name':'notes.read','description':'Read a synthetic note','inputSchema':{'type':'object'}}]}}
    elif payload['method']=='notifications/initialized':
      return httpx.Response(202,headers={'content-type':'application/json'},
        stream=httpx.ByteStream(b''))
    else:raise AssertionError('Unexpected synthetic MCP method')
    return httpx.Response(200,headers={'content-type':'application/json'},
      stream=httpx.ByteStream(json.dumps(body).encode()))
  return handle


@pytest.mark.asyncio
async def test_generic_http_client_uses_configured_key_header():
  calls=[]
  app=create_gateway(load(ROOT/'deploy/selfhost/deployment.yaml'),CLIENT_KEY,SIGNING_KEY,
    transport=httpx.MockTransport(synthetic_target(calls)))
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://gateway.test',
      headers={'x-td-client-key':CLIENT_KEY}) as client:
    response=await client.post('/api/notes',json={'message':'safe'})
  assert response.status_code==200 and response.json()['received']=={'message':'safe'}
  assert len(calls)==1 and calls[0].url.path=='/api/notes'


@pytest.mark.asyncio
async def test_official_mcp_sdk_initializes_and_discovers_tools():
  assert version('mcp')=='1.30.0'
  calls=[]
  app=create_gateway(load(ROOT/'deploy/selfhost/deployment.yaml'),CLIENT_KEY,SIGNING_KEY,
    transport=httpx.MockTransport(synthetic_target(calls)))
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://gateway.test',
      headers={'x-td-client-key':CLIENT_KEY}) as client:
    async with streamable_http_client('http://gateway.test/mcp',http_client=client,
        terminate_on_close=False) as (read_stream,write_stream,_):
      async with ClientSession(read_stream,write_stream) as session:
        initialized=await session.initialize()
        tools=await session.list_tools()
  assert initialized.protocolVersion=='2025-11-25'
  assert [tool.name for tool in tools.tools]==['notes.read']
  assert [json.loads(call.content)['method'] for call in calls]==[
    'initialize','notifications/initialized','tools/list']
  assert calls[-1].headers['mcp-protocol-version']=='2025-11-25'
