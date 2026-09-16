"""Browser-bound, single-use SSO transactions and isolated synthetic issuer."""
import html
import secrets
import threading
import time
from urllib.parse import urlencode

from fastapi import HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from .identity import IdentityError, challenge

FLOW_COOKIE='td_console_oidc'


def install_sso(app,identity,store,session_cookie):
  transactions={};codes={};lock=threading.Lock()
  private_key=None
  if identity.synthetic:
    from cryptography.hazmat.primitives.asymmetric import rsa
    private_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)

  @app.post('/demo-api/auth/start')
  def start(response: Response):
    state,verifier,nonce,url=identity.start();binding=secrets.token_urlsafe(32)
    with lock:
      now=time.time()
      for key in list(transactions):
        if transactions[key]['expires']<now:del transactions[key]
      if len(transactions)>=1000:raise HTTPException(429,'Too many pending sign-ins.')
      transactions[state]=dict(verifier=verifier,nonce=nonce,binding=binding,expires=now+300)
    response.set_cookie(FLOW_COOKIE,binding,httponly=True,samesite='lax',secure=identity.origin.startswith('https:'),path='/demo-api/auth',max_age=300)
    return {'url':url}

  @app.get('/demo-api/auth/callback')
  def callback(request:Request):
    state=request.query_params.get('state','')
    with lock:
      pending=transactions.get(state)
      if not pending or pending['expires']<time.time() or not secrets.compare_digest(pending['binding'],request.cookies.get(FLOW_COOKIE,'')):
        raise HTTPException(400,'Sign-in expired or browser binding failed.')
      transactions.pop(state)
    try:
      code=request.query_params.get('code','')
      if not code or len(code)>8192:raise IdentityError('Missing authorization code.')
      if identity.synthetic:
        with lock:authorization=codes.pop(code,None)
        if not authorization or authorization['expires']<time.time() or authorization['challenge']!=challenge(pending['verifier']):raise IdentityError('Synthetic PKCE validation failed.')
        import jwt
        now=int(time.time())
        encoded=jwt.encode(dict(iss=identity.issuer,aud=identity.client,sub='synthetic-'+authorization['role'],oid='synthetic-'+authorization['role'],tid=identity.tenant,nonce=authorization['nonce'],iat=now,exp=now+3600,roles=['TrapDefense.'+authorization['role'].title()]),private_key,algorithm='RS256')
        principal=identity.validate(encoded,private_key.public_key(),pending['nonce'])
      else:principal=identity.exchange(code,pending['verifier'],pending['nonce'])
    except IdentityError:
      store.audit('account.sso_failed','Identity validation or role assignment failed',actor='anonymous')
      response=RedirectResponse('/?signin=failed',status_code=303)
      response.delete_cookie(FLOW_COOKIE,path='/demo-api/auth')
      return response
    store.logout(request.cookies.get(session_cookie))
    ttl=max(1,min(3600,int(principal.pop('expires')-time.time())))
    token=store.create_session(principal,ttl=ttl)
    response=RedirectResponse('/',status_code=303)
    response.set_cookie(session_cookie,token,httponly=True,samesite='lax',secure=identity.origin.startswith('https:'),path='/demo-api',max_age=ttl)
    response.delete_cookie(FLOW_COOKIE,path='/demo-api/auth')
    store.audit('account.sso_login',principal['authentication']+' / '+principal['role'],actor=principal['tenant_id']+'/'+principal['object_id'])
    return response

  if identity.synthetic:
    @app.get('/demo-api/auth/synthetic/authorize')
    def authorize(request:Request):
      q=request.query_params
      if q.get('client_id')!=identity.client or q.get('redirect_uri')!=identity.redirect or q.get('code_challenge_method')!='S256' or q.get('response_type')!='code':raise HTTPException(400,'Invalid synthetic client.')
      with lock:
        pending=transactions.get(q.get('state'))
        if not pending or pending['expires']<time.time() or pending['nonce']!=q.get('nonce') or challenge(pending['verifier'])!=q.get('code_challenge') or not secrets.compare_digest(pending['binding'],request.cookies.get(FLOW_COOKIE,'')):raise HTTPException(400,'Invalid synthetic transaction.')
      role=q.get('demo_role')
      if role not in ('admin','viewer'):
        links=''.join('<p><a href="'+html.escape(str(request.url)+'&demo_role='+role,quote=True)+'">'+role.title()+'</a></p>' for role in ('admin','viewer'))
        return HTMLResponse('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width"><title>Synthetic Entra sign-in</title><main style="font:18px system-ui;max-width:600px;margin:10vh auto;padding:24px"><h1>Synthetic Entra sign-in</h1><p>Local protocol demo. No Microsoft account or real tenant is used.</p><p>Select the console app role:</p>'+links+'</main></html>')
      code=secrets.token_urlsafe(32)
      with lock:
        for key in list(codes):
          if codes[key]['expires']<time.time():del codes[key]
        if len(codes)>=1000:raise HTTPException(429,'Too many synthetic codes.')
        codes[code]=dict(role=role,nonce=q['nonce'],challenge=q['code_challenge'],expires=time.time()+60)
      return RedirectResponse(identity.redirect+'?'+urlencode(dict(code=code,state=q['state'])),status_code=303)
