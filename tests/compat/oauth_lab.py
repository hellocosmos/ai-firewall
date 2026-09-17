"""Standards-shaped OAuth authorization server used only by compatibility tests."""
from dataclasses import dataclass
import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlencode

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
import jwt


GATEWAY_ORIGIN='http://127.0.0.1:19184'
ISSUER_ORIGIN='http://127.0.0.1:19185'
RESOURCE=GATEWAY_ORIGIN+'/mcp'
CLIENT_ID='synthetic-mcp-client'


@dataclass(frozen=True)
class ProviderProfile:
  name: str
  slug: str
  audience: str
  scope_claim: str
  scope_array: bool
  party_claim: str
  extra_claims: dict

  @property
  def issuer(self):return f'{ISSUER_ORIGIN}/{self.slug}'


PROFILES=(
  ProviderProfile('entra','entra/v2.0','11111111-2222-3333-4444-555555555555','scp',False,'azp',{
    'tid':'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee','oid':'synthetic-entra-object'}),
  ProviderProfile('okta','oauth2/default','api://trapdefense','scp',True,'cid',{
    'uid':'synthetic-okta-user','ver':1}),
  ProviderProfile('keycloak','realms/trapdefense','trapdefense-gateway','scope',False,'azp',{
    'realm_access':{'roles':['mcp-user']}}),
)


class OAuthLab:
  def __init__(self,profile: ProviderProfile):
    self.profile=profile
    self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    self.codes={}
    self.observed={'metadata':0,'registration':0,'authorize':[],'token':[]}
    self.app=FastAPI(openapi_url=None,docs_url=None,redoc_url=None)
    self._routes()

  def _routes(self):
    profile=self.profile

    @self.app.get('/.well-known/oauth-authorization-server/{path:path}')
    @self.app.get('/.well-known/openid-configuration/{path:path}')
    @self.app.get('/{path:path}/.well-known/openid-configuration')
    async def metadata(path: str):
      if path.rstrip('/')!=profile.slug:return JSONResponse({'error':'not_found'},status_code=404)
      self.observed['metadata']+=1
      return {
        'issuer':profile.issuer,
        'authorization_endpoint':profile.issuer+'/authorize',
        'token_endpoint':profile.issuer+'/token',
        'registration_endpoint':profile.issuer+'/register',
        'jwks_uri':profile.issuer+'/jwks',
        'response_types_supported':['code'],
        'grant_types_supported':['authorization_code'],
        'token_endpoint_auth_methods_supported':['none'],
        'code_challenge_methods_supported':['S256'],
        'scopes_supported':['mcp.invoke'],
      }

    @self.app.get('/{path:path}/jwks')
    async def jwks(path: str):
      if path.rstrip('/')!=profile.slug:return JSONResponse({'error':'not_found'},status_code=404)
      key=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
      key.update(kid=f'{profile.name}-synthetic-key',use='sig',alg='RS256')
      return {'keys':[key]}

    @self.app.post('/{path:path}/register')
    async def register(path: str,request: Request):
      if path.rstrip('/')!=profile.slug:return JSONResponse({'error':'not_found'},status_code=404)
      payload=await request.json()
      self.observed['registration']+=1
      return JSONResponse({
        **payload,'client_id':CLIENT_ID,'token_endpoint_auth_method':'none',
      },status_code=201)

    @self.app.get('/{path:path}/authorize')
    async def authorize(path: str,request: Request):
      if path.rstrip('/')!=profile.slug:return JSONResponse({'error':'not_found'},status_code=404)
      query=dict(request.query_params)
      self.observed['authorize'].append(query)
      required=('client_id','redirect_uri','state','code_challenge','resource')
      if any(not query.get(name) for name in required):
        return JSONResponse({'error':'invalid_request'},status_code=400)
      if query['client_id']!=CLIENT_ID or query['resource']!=RESOURCE:
        return JSONResponse({'error':'invalid_target'},status_code=400)
      code=f'{profile.name}-authorization-code'
      self.codes[code]={'challenge':query['code_challenge'],'client_id':query['client_id'],
        'redirect_uri':query['redirect_uri'],'resource':query['resource']}
      separator='&' if '?' in query['redirect_uri'] else '?'
      location=query['redirect_uri']+separator+urlencode({'code':code,'state':query['state']})
      return RedirectResponse(location,status_code=302)

    @self.app.post('/{path:path}/token')
    async def token(path: str,request: Request):
      if path.rstrip('/')!=profile.slug:return JSONResponse({'error':'not_found'},status_code=404)
      form={name:values[0] for name,values in parse_qs((await request.body()).decode()).items()}
      self.observed['token'].append(form)
      code=self.codes.pop(form.get('code',''),None)
      if not code:return JSONResponse({'error':'invalid_grant'},status_code=400)
      challenge=base64.urlsafe_b64encode(hashlib.sha256(form.get('code_verifier','').encode()).digest()).decode().rstrip('=')
      if (challenge!=code['challenge'] or form.get('client_id')!=code['client_id']
          or form.get('redirect_uri')!=code['redirect_uri'] or form.get('resource')!=code['resource']):
        return JSONResponse({'error':'invalid_grant'},status_code=400)
      return {'access_token':self.access_token(),'token_type':'Bearer','expires_in':300,'scope':'mcp.invoke'}

  def access_token(self,**updates):
    now=int(time.time())
    claims={'iss':self.profile.issuer,'aud':self.profile.audience,'sub':f'{self.profile.name}-subject',
      'iat':now,'exp':now+300,self.profile.party_claim:CLIENT_ID,**self.profile.extra_claims}
    claims[self.profile.scope_claim]=['mcp.invoke'] if self.profile.scope_array else 'mcp.invoke'
    claims.update(updates)
    return jwt.encode(claims,self.key,algorithm='RS256',headers={'kid':f'{self.profile.name}-synthetic-key'})


class HostRouter:
  def __init__(self,gateway,issuer):self.gateway,self.issuer=gateway,issuer

  async def __call__(self,scope,receive,send):
    host=dict(scope.get('headers',[])).get(b'host',b'').decode().lower()
    app=self.issuer if host==f'127.0.0.1:19185' else self.gateway
    await app(scope,receive,send)


class MemoryStorage:
  def __init__(self):self.tokens,self.client=None,None
  async def get_tokens(self):return self.tokens
  async def set_tokens(self,tokens):self.tokens=tokens
  async def get_client_info(self):return self.client
  async def set_client_info(self,client):self.client=client
