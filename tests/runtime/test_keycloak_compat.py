"""Opt-in integration with an unmodified official Keycloak container."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
import jwt
import pytest

from asr_proxy.selfhost.config import Deployment,load
from asr_proxy.selfhost.gateway import create_gateway


ROOT=Path(__file__).parents[2]
IMAGE='quay.io/keycloak/keycloak@sha256:29be7252db0a106f1cd2ac17b9a56ff2668073da645638a38b9fc67deeb2d6c4'
CLIENT_KEY='synthetic-client-'+'x'*32
SIGNING_KEY=b'synthetic-signing-key-'+b'x'*32


def free_port():
  with socket.socket() as handle:
    handle.bind(('127.0.0.1',0))
    return handle.getsockname()[1]


def wait_for(url,timeout=120):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
    try:
      response=httpx.get(url,timeout=1)
      if response.status_code==200:return response
    except httpx.HTTPError:pass
    time.sleep(.25)
  raise AssertionError(f'Keycloak did not become ready at {url}')


@pytest.mark.skipif(os.getenv('TD_KEYCLOAK_E2E')!='1',reason='Set TD_KEYCLOAK_E2E=1')
def test_real_keycloak_token_is_accepted_and_consumed():
  if not shutil.which('docker'):pytest.skip('docker is unavailable')
  port=free_port()
  name='trapdefense-keycloak-'+uuid4().hex[:10]
  issuer=f'http://127.0.0.1:{port}/realms/trapdefense-lab'
  realm=(ROOT/'tests/fixtures/keycloak/trapdefense-lab-realm.json').resolve()
  command=['docker','run','--detach','--rm','--name',name,
    '--publish',f'127.0.0.1:{port}:8080',
    '--env','KC_BOOTSTRAP_ADMIN_USERNAME=synthetic-admin',
    '--env','KC_BOOTSTRAP_ADMIN_PASSWORD=synthetic-admin-password',
    '--volume',f'{realm}:/opt/keycloak/data/import/trapdefense-lab-realm.json:ro',
    IMAGE,'start-dev','--import-realm',f'--hostname=http://127.0.0.1:{port}']
  subprocess.run(command,check=True,capture_output=True,text=True)
  try:
    metadata=wait_for(issuer+'/.well-known/openid-configuration').json()
    token_response=httpx.post(metadata['token_endpoint'],data={
      'grant_type':'client_credentials','client_id':'trapdefense-lab-client',
      'client_secret':'synthetic-keycloak-client-secret','scope':'mcp.invoke',
    },timeout=10)
    assert token_response.status_code==200,token_response.text
    token=token_response.json()['access_token']
    claims=jwt.decode(token,options={'verify_signature':False})
    assert claims['iss']==issuer and claims['aud']=='trapdefense-gateway'
    assert 'mcp.invoke' in claims['scope'].split() and claims['azp']=='trapdefense-lab-client'

    data=load(ROOT/'deploy/selfhost/deployment.yaml').model_dump(exclude_none=True)
    data.update(target_auth={'mode':'none'},gateway_auth={
      'mode':'jwt','issuer':issuer,'audience':'trapdefense-gateway','jwks_uri':metadata['jwks_uri'],
      'resource':'http://127.0.0.1:19184/mcp','authorization_servers':[issuer],
      'required_scopes':['mcp.invoke'],'authorized_parties':['trapdefense-lab-client'],
      'allow_insecure_loopback':True,
    })
    config=Deployment.model_validate(data)
    receipts=[]
    def target(request):
      receipts.append(request)
      assert request.headers.get('authorization') is None
      body={'jsonrpc':'2.0','id':1,'result':{'protocolVersion':'2025-11-25',
        'capabilities':{},'serverInfo':{'name':'keycloak-target','version':'0.38'}}}
      return httpx.Response(200,headers={'content-type':'application/json'},
        stream=httpx.ByteStream(json.dumps(body).encode()))
    app=create_gateway(config,CLIENT_KEY,SIGNING_KEY,transport=httpx.MockTransport(target))
    response=TestClient(app).post('/mcp',headers={'authorization':'Bearer '+token},json={
      'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25',
      'capabilities':{},'clientInfo':{'name':'keycloak-test','version':'0.38'}}})
    assert response.status_code==200 and len(receipts)==1
  finally:
    subprocess.run(['docker','rm','--force',name],capture_output=True,text=True)
