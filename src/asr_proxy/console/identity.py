"""Single-tenant console identity. ID tokens never authorize agent actions."""
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import httpx
import jwt


class IdentityError(ValueError):pass


def challenge(verifier):
  return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')


class Identity:
  def __init__(self,config,*,synthetic=False):
    self.synthetic=synthetic
    self.tenant=str(UUID(config['tenant_id']))
    self.client=str(UUID(config['client_id']))
    self.secret=config.get('client_secret','')
    self.redirect=config['redirect_uri']
    parsed=urlsplit(self.redirect)
    loopback=parsed.hostname in ('localhost','127.0.0.1')
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path!='/demo-api/auth/callback' or (parsed.scheme!='https' and not (parsed.scheme=='http' and loopback)):
      raise IdentityError('Use an HTTPS callback or explicit loopback callback.')
    if synthetic and not loopback:raise IdentityError('Synthetic identity requires loopback.')
    if not synthetic and not self.secret:raise IdentityError('Entra web app client secret is required.')
    self.origin=f'{parsed.scheme}://{parsed.netloc}'
    self.issuer=f'https://login.microsoftonline.com/{self.tenant}/v2.0'
    self.base=f'https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0'
    self.keys=jwt.PyJWKClient(f'https://login.microsoftonline.com/{self.tenant}/discovery/v2.0/keys',timeout=5,lifespan=300)

  def start(self):
    state,verifier,nonce=(secrets.token_urlsafe(32) for _ in range(3))
    endpoint=self.origin+'/demo-api/auth/synthetic/authorize' if self.synthetic else self.base+'/authorize'
    query=dict(client_id=self.client,response_type='code',redirect_uri=self.redirect,response_mode='query',scope='openid profile',state=state,nonce=nonce,code_challenge=challenge(verifier),code_challenge_method='S256')
    return state,verifier,nonce,endpoint+'?'+urlencode(query)

  def validate(self,encoded,key,nonce):
    try:
      claims=jwt.decode(encoded,key,algorithms=['RS256'],audience=self.client,issuer=self.issuer,options={'require':['iss','aud','sub','exp','iat','nonce','tid','oid']})
      roles=claims.get('roles')
      if claims['tid']!=self.tenant or claims['nonce']!=nonce or not isinstance(claims['oid'],str) or not claims['oid'] or not isinstance(roles,list) or not all(isinstance(r,str) for r in roles):raise IdentityError('Invalid identity claims.')
      if claims.get('azp',self.client)!=self.client:raise IdentityError('Invalid authorized party.')
      role='admin' if 'TrapDefense.Admin' in roles else 'viewer' if 'TrapDefense.Viewer' in roles else None
      if role is None:raise IdentityError('Assign TrapDefense.Admin or TrapDefense.Viewer.')
      return {'username':claims['oid'],'object_id':claims['oid'],'tenant_id':self.tenant,'client_id':self.client,'role':role,'authentication':'synthetic_entra' if self.synthetic else 'entra','expires':claims['exp']}
    except (jwt.PyJWTError,TypeError,KeyError) as exc:raise IdentityError('Identity validation failed.') from None

  def exchange(self,code,verifier,nonce):
    try:
      with httpx.Client(timeout=8,follow_redirects=False) as client:
        response=client.post(self.base+'/token',data=dict(client_id=self.client,client_secret=self.secret,grant_type='authorization_code',code=code,redirect_uri=self.redirect,code_verifier=verifier))
        response.raise_for_status();encoded=response.json()['id_token']
      key=self.keys.get_signing_key_from_jwt(encoded).key
      return self.validate(encoded,key,nonce)
    except (httpx.HTTPError,jwt.PyJWTError,ValueError,KeyError):raise IdentityError('Entra sign-in failed. Check configuration and role assignment.') from None
