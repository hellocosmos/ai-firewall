"""Full OAuth discovery, PKCE and MCP flow for representative provider dialects."""
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlparse

import httpx
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientMetadata
import pytest

from asr_proxy.selfhost.config import Deployment,load
from asr_proxy.selfhost.auth import GatewayAuthenticator
from asr_proxy.selfhost.gateway import create_gateway
from .oauth_lab import CLIENT_ID,GATEWAY_ORIGIN,HostRouter,MemoryStorage,OAuthLab,PROFILES,RESOURCE


ROOT=Path(__file__).parents[2]
CLIENT_KEY='synthetic-client-'+'x'*32
SIGNING_KEY=b'synthetic-signing-key-'+b'x'*32


class LabKeys:
  def __init__(self,key):self.key=key
  def get_signing_key_from_jwt(self,token):return SimpleNamespace(key=self.key.public_key())


def deployment(profile):
  data=load(ROOT/'deploy/selfhost/deployment.yaml').model_dump(exclude_none=True)
  data.update(target_auth={'mode':'none'},gateway_auth={
    'mode':'jwt','issuer':profile.issuer,'audience':profile.audience,
    'jwks_uri':profile.issuer+'/jwks','resource':RESOURCE,
    'authorization_servers':[profile.issuer],'required_scopes':['mcp.invoke'],
    'authorized_parties':[CLIENT_ID],'allow_insecure_loopback':True,
  })
  return Deployment.model_validate(data)


def target(receipts):
  def handle(request):
    receipts.append(request)
    assert request.headers.get('authorization') is None
    payload=json.loads(request.content)
    if payload['method']=='initialize':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{'protocolVersion':'2025-11-25',
        'capabilities':{},'serverInfo':{'name':'trapdefense-oauth-lab','version':'0.38'}}}
    elif payload['method']=='notifications/initialized':
      return httpx.Response(202,headers={'content-type':'application/json'},stream=httpx.ByteStream(b''))
    elif payload['method']=='tools/list':
      body={'jsonrpc':'2.0','id':payload['id'],'result':{'tools':[
        {'name':'notes.read','description':'Read synthetic notes','inputSchema':{'type':'object'}}]}}
    else:raise AssertionError(f'Unexpected method: {payload["method"]}')
    return httpx.Response(200,headers={'content-type':'application/json'},
      stream=httpx.ByteStream(json.dumps(body).encode()))
  return handle


@pytest.mark.asyncio
@pytest.mark.parametrize('profile',PROFILES,ids=lambda profile:profile.name)
async def test_provider_profile_completes_oauth_pkce_and_current_mcp(profile):
  lab=OAuthLab(profile)
  receipts=[]
  configured=deployment(profile)
  authenticator=GatewayAuthenticator(configured.gateway_auth,client_key=CLIENT_KEY,
    jwk_client=LabKeys(lab.key))
  gateway=create_gateway(configured,CLIENT_KEY,SIGNING_KEY,authenticator=authenticator,
    transport=httpx.MockTransport(target(receipts)))
  router=HostRouter(gateway,lab.app)
  callback={}

  async def redirect_handler(url):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router)) as browser:
      response=await browser.get(url,follow_redirects=False)
    assert response.status_code==302
    callback.update({name:values[0] for name,values in parse_qs(urlparse(response.headers['location']).query).items()})

  async def callback_handler():return callback['code'],callback['state']

  oauth=OAuthClientProvider(RESOURCE,OAuthClientMetadata(
    redirect_uris=['http://127.0.0.1:19186/callback'],token_endpoint_auth_method='none',
    grant_types=['authorization_code'],response_types=['code'],scope='mcp.invoke',
    client_name='TrapDefense Compatibility Lab'),MemoryStorage(),redirect_handler,callback_handler)
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router),base_url=GATEWAY_ORIGIN,
      auth=oauth) as client:
    async with streamable_http_client(RESOURCE,http_client=client,terminate_on_close=False) as streams:
      async with ClientSession(streams[0],streams[1]) as session:
        initialized=await session.initialize()
        tools=await session.list_tools()

  assert initialized.protocolVersion=='2025-11-25'
  assert [tool.name for tool in tools.tools]==['notes.read']
  assert lab.observed['metadata']>=1 and lab.observed['registration']==1
  assert lab.observed['authorize'][0]['resource']==RESOURCE
  assert lab.observed['token'][0]['resource']==RESOURCE
  assert [json.loads(receipt.content)['method'] for receipt in receipts]==[
    'initialize','notifications/initialized','tools/list']


@pytest.mark.asyncio
async def test_token_from_another_provider_is_rejected():
  configured=OAuthLab(PROFILES[0])
  foreign=OAuthLab(PROFILES[1])
  config=deployment(PROFILES[0])
  authenticator=GatewayAuthenticator(config.gateway_auth,client_key=CLIENT_KEY,
    jwk_client=LabKeys(configured.key))
  gateway=create_gateway(config,CLIENT_KEY,SIGNING_KEY,authenticator=authenticator,
    transport=httpx.MockTransport(lambda request:pytest.fail('foreign token reached target')))
  router=HostRouter(gateway,configured.app)
  # Exercise the ASGI gateway directly; rejection may occur on signature or issuer before forwarding.
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router),base_url=GATEWAY_ORIGIN) as client:
    response=await client.post('/mcp',headers={'authorization':'Bearer '+foreign.access_token()},json={})
  assert response.status_code==401 and response.json()=={'error':'invalid_token'}
