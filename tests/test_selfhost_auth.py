"""Gateway caller authentication and independent target credentials."""
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from asr_proxy.selfhost.auth import AuthError, GatewayAuthenticator
from asr_proxy.selfhost.config import ClientKeyGatewayAuth, JwtGatewayAuth, TargetAuth
from asr_proxy.selfhost.credentials import CredentialError, TargetCredentialProvider


ISSUER='https://issuer.example/tenant'
RESOURCE='https://firewall.example/mcp'
AUDIENCE=RESOURCE
CLIENT_KEY='synthetic-client-'+'x'*32


@pytest.fixture(scope='module')
def signing_key():return rsa.generate_private_key(public_exponent=65537,key_size=2048)


def auth_config(**updates):
  data={
    'issuer':ISSUER,'audience':AUDIENCE,'jwks_uri':'https://issuer.example/jwks',
    'resource':RESOURCE,'authorization_servers':[ISSUER],'required_scopes':['mcp.invoke'],
  }
  data.update(updates)
  return JwtGatewayAuth(**data)


def encoded(signing_key,**updates):
  now=int(time.time())
  claims={'iss':ISSUER,'aud':AUDIENCE,'sub':'synthetic-agent','iat':now,'exp':now+300,
          'scope':'mcp.invoke notes.read'}
  for name,value in updates.items():
    if value is None:claims.pop(name,None)
    else:claims[name]=value
  return jwt.encode(claims,signing_key,algorithm='RS256',headers={'kid':'synthetic-key'})


class KeyClient:
  def __init__(self,key=None,error=None):self.key,self.error=key,error
  def get_signing_key_from_jwt(self,token):
    if self.error:raise self.error
    return SimpleNamespace(key=self.key.public_key())


def test_client_key_authentication_is_constant_boundary():
  auth=GatewayAuthenticator(ClientKeyGatewayAuth(),client_key=CLIENT_KEY)
  result=auth.authenticate({'x-td-client-key':CLIENT_KEY})
  assert result.subject=='client-key' and result.scopes==frozenset()
  with pytest.raises(AuthError) as missing:auth.authenticate({})
  assert missing.value.status_code==401 and missing.value.code=='invalid_client_key'
  assert auth.metadata() is None and auth.challenge() is None


def test_valid_jwt_and_resource_metadata(signing_key):
  auth=GatewayAuthenticator(auth_config(),client_key=CLIENT_KEY,jwk_client=KeyClient(signing_key))
  result=auth.authenticate({'authorization':'Bearer '+encoded(signing_key)})
  assert result.subject=='synthetic-agent'
  assert result.scopes==frozenset({'mcp.invoke','notes.read'})
  assert result.identity=={}
  assert auth.metadata()=={
    'resource':RESOURCE,'authorization_servers':[ISSUER],
    'bearer_methods_supported':['header'],'scopes_supported':['mcp.invoke']}
  assert auth.challenge()=='Bearer resource_metadata="https://firewall.example/.well-known/oauth-protected-resource/mcp"'


def test_okta_array_scope_and_authorized_party_claims(signing_key):
  auth=GatewayAuthenticator(auth_config(authorized_parties=['expected-client']),client_key=CLIENT_KEY,
    jwk_client=KeyClient(signing_key))
  result=auth.authenticate({'authorization':'Bearer '+encoded(signing_key,
    scope=None,scp=['mcp.invoke','notes.read'],cid='expected-client')})
  assert result.scopes==frozenset({'mcp.invoke','notes.read'})


def test_explicit_identity_claim_map_returns_only_normalized_values(signing_key):
  auth=GatewayAuthenticator(auth_config(identity_claims={}),client_key=CLIENT_KEY,
    jwk_client=KeyClient(signing_key))
  token=encoded(signing_key,tid='tenant-a',agent_id='agent-a',delegation_id='delegation-a',
    task_id='task-a',agent_instance_id='instance-a',untrusted='must-not-propagate')
  result=auth.authenticate({'authorization':'Bearer '+token})
  assert result.identity=={
    'tenant_id':'tenant-a','user_id':'synthetic-agent','agent_id':'agent-a',
    'delegation_id':'delegation-a','task_id':'task-a','agent_instance_id':'instance-a'}
  assert 'untrusted' not in result.identity


def test_missing_required_mapped_identity_fails_closed(signing_key):
  auth=GatewayAuthenticator(auth_config(identity_claims={}),client_key=CLIENT_KEY,
    jwk_client=KeyClient(signing_key))
  with pytest.raises(AuthError) as error:
    auth.authenticate({'authorization':'Bearer '+encoded(signing_key,tid='tenant-a')})
  assert error.value.code=='invalid_agent_identity'


@pytest.mark.parametrize(('claim','value'),[
  ('azp','expected-client'),('appid','expected-client'),('cid','expected-client'),
])
def test_common_authorized_party_claims(signing_key,claim,value):
  auth=GatewayAuthenticator(auth_config(authorized_parties=[value]),client_key=CLIENT_KEY,
    jwk_client=KeyClient(signing_key))
  assert auth.authenticate({'authorization':'Bearer '+encoded(signing_key,**{claim:value})}).subject=='synthetic-agent'


def test_wrong_or_missing_authorized_party_fails_closed(signing_key):
  auth=GatewayAuthenticator(auth_config(authorized_parties=['expected-client']),client_key=CLIENT_KEY,
    jwk_client=KeyClient(signing_key))
  for updates in ({},{'azp':'wrong-client'}):
    with pytest.raises(AuthError) as error:
      auth.authenticate({'authorization':'Bearer '+encoded(signing_key,**updates)})
    assert error.value.code=='invalid_token'


@pytest.mark.parametrize('headers',[
  {}, {'authorization':'Basic abc'}, {'authorization':'Bearer'},
  {'authorization':'Bearer one two'},
])
def test_malformed_or_missing_jwt_fails_closed(signing_key,headers):
  auth=GatewayAuthenticator(auth_config(),client_key=CLIENT_KEY,jwk_client=KeyClient(signing_key))
  with pytest.raises(AuthError) as error:auth.authenticate(headers)
  assert error.value.status_code==401 and error.value.code=='invalid_token'


@pytest.mark.parametrize('updates',[
  {'iss':'https://other.example'}, {'aud':'https://other.example/mcp'},
  {'exp':1}, {'sub':''}, {'iat':'not-an-integer'},
])
def test_invalid_jwt_claims_fail_closed(signing_key,updates):
  auth=GatewayAuthenticator(auth_config(),client_key=CLIENT_KEY,jwk_client=KeyClient(signing_key))
  with pytest.raises(AuthError) as error:
    auth.authenticate({'authorization':'Bearer '+encoded(signing_key,**updates)})
  assert error.value.status_code==401 and error.value.code=='invalid_token'


def test_missing_scope_returns_forbidden(signing_key):
  auth=GatewayAuthenticator(auth_config(required_scopes=['mcp.invoke','notes.write']),
                            client_key=CLIENT_KEY,jwk_client=KeyClient(signing_key))
  with pytest.raises(AuthError) as error:
    auth.authenticate({'authorization':'Bearer '+encoded(signing_key)})
  assert error.value.status_code==403 and error.value.code=='insufficient_scope'
  assert 'scope="mcp.invoke notes.write"' in auth.challenge(error.value)


def test_jwks_error_is_sanitized(signing_key):
  auth=GatewayAuthenticator(auth_config(),client_key=CLIENT_KEY,
    jwk_client=KeyClient(error=jwt.PyJWKClientError('contains private endpoint detail')))
  with pytest.raises(AuthError) as error:
    auth.authenticate({'authorization':'Bearer '+encoded(signing_key)})
  assert str(error.value)=='invalid_token'


def test_protocol_realistic_synthetic_jwks_lookup(signing_key):
  public=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(signing_key.public_key()))
  public.update(kid='synthetic-key',use='sig',alg='RS256')
  documents=[json.dumps({'keys':[public]}).encode()]
  class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
      if self.path!='/jwks':self.send_error(404);return
      document=documents[0]
      self.send_response(200);self.send_header('Content-Type','application/json')
      self.send_header('Content-Length',str(len(document)));self.end_headers();self.wfile.write(document)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
    issuer=f'http://127.0.0.1:{server.server_port}'
    resource='http://127.0.0.1:18084/mcp'
    config=auth_config(issuer=issuer,audience=resource,jwks_uri=issuer+'/jwks',resource=resource,
      authorization_servers=[issuer],allow_insecure_loopback=True)
    now=int(time.time())
    token=jwt.encode({'iss':issuer,'aud':resource,'sub':'synthetic-agent','iat':now,'exp':now+300,
      'scope':'mcp.invoke'},signing_key,algorithm='RS256',headers={'kid':'synthetic-key'})
    authenticator=GatewayAuthenticator(config,client_key=CLIENT_KEY)
    result=authenticator.authenticate({'authorization':'Bearer '+token})
    assert result.subject=='synthetic-agent'
    rotated=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    rotated_public=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(rotated.public_key()))
    rotated_public.update(kid='rotated-key',use='sig',alg='RS256')
    documents[0]=json.dumps({'keys':[rotated_public]}).encode()
    time.sleep(5.05)
    rotated_token=jwt.encode({'iss':issuer,'aud':resource,'sub':'rotated-agent','iat':now,
      'exp':now+300,'scope':'mcp.invoke'},rotated,algorithm='RS256',headers={'kid':'rotated-key'})
    assert authenticator.authenticate({'authorization':'Bearer '+rotated_token}).subject=='rotated-agent'
  finally:
    server.shutdown();server.server_close();thread.join(timeout=2)


@pytest.mark.parametrize(('target','gateway_mode','inbound','expected'),[
  (TargetAuth(mode='none'),'jwt','Bearer gateway-token',{}),
  (TargetAuth(mode='passthrough_bearer'),'client_key','Bearer service-token',
   {'authorization':'Bearer service-token'}),
  (TargetAuth(mode='static_bearer',secret_file='/state/token'),'client_key',None,
   {'authorization':'Bearer target-token'}),
  (TargetAuth(mode='static_api_key',secret_file='/state/key',header='Ocp-Apim-Subscription-Key',prefix='ApiKey '),
   'client_key',None,{'ocp-apim-subscription-key':'ApiKey target-token'}),
])
def test_target_credentials_are_applied_independently(target,gateway_mode,inbound,expected):
  secret='target-token' if target.secret_file else None
  provider=TargetCredentialProvider(target,gateway_mode=gateway_mode,secret=secret)
  result=provider.apply({'content-type':'application/json'},inbound)
  assert result=={'content-type':'application/json',**expected}


@pytest.mark.parametrize(('target','gateway_mode','headers','inbound'),[
  (TargetAuth(mode='none'),'client_key',{},'Bearer unexpected'),
  (TargetAuth(mode='static_bearer',secret_file='/state/token'),'client_key',{},'Bearer unexpected'),
  (TargetAuth(mode='static_api_key',secret_file='/state/key',header='x-api-key'),
   'client_key',{'x-api-key':'caller-value'},None),
  (TargetAuth(mode='passthrough_bearer'),'client_key',{},'Basic unsupported'),
])
def test_target_credential_conflicts_fail_before_forward(target,gateway_mode,headers,inbound):
  provider=TargetCredentialProvider(target,gateway_mode=gateway_mode,
    secret='target-token' if target.secret_file else None)
  with pytest.raises(CredentialError):provider.apply(headers,inbound)
