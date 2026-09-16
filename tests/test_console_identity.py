"""Console SSO validates identity and enforces server-side roles."""
import time
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from asr_proxy.console.identity import Identity, IdentityError

TENANT='11111111-1111-4111-8111-111111111111'
CLIENT='22222222-2222-4222-8222-222222222222'

@pytest.fixture
def identity():
  return Identity({'tenant_id':TENANT,'client_id':CLIENT,'client_secret':'test-only','redirect_uri':'http://localhost:5176/demo-api/auth/callback'})

@pytest.fixture
def key():return rsa.generate_private_key(public_exponent=65537,key_size=2048)

def token(key,**changes):
  claims=dict(iss=f'https://login.microsoftonline.com/{TENANT}/v2.0',aud=CLIENT,sub='subject',oid='operator-object',tid=TENANT,nonce='nonce',iat=int(time.time()),exp=int(time.time())+300,roles=['TrapDefense.Viewer'])
  claims.update(changes)
  return jwt.encode(claims,key,algorithm='RS256',headers={'kid':'test'})

def test_role_validation(identity,key):
  assert identity.validate(token(key),key.public_key(),'nonce')['role']=='viewer'
  assert identity.validate(token(key,roles=['TrapDefense.Admin']),key.public_key(),'nonce')['role']=='admin'

@pytest.mark.parametrize('changes',[{'aud':'other'},{'tid':'other'},{'iss':'https://evil.test'},{'exp':0},{'nonce':'other'},{'roles':[]},{'roles':'TrapDefense.Admin'},{'oid':''}])
def test_reject_bad_claims(identity,key,changes):
  with pytest.raises(IdentityError):identity.validate(token(key,**changes),key.public_key(),'nonce')

def test_reject_bad_signature(identity,key):
  wrong=rsa.generate_private_key(public_exponent=65537,key_size=2048)
  with pytest.raises(IdentityError):identity.validate(token(wrong),key.public_key(),'nonce')

from urllib.parse import urlsplit,parse_qs
from fastapi.testclient import TestClient
from asr_proxy.console.app import create_app
HEADERS={'origin':'http://127.0.0.1:5176','x-td-demo':'1'}

def synthetic():
  return Identity({'tenant_id':TENANT,'client_id':CLIENT,'redirect_uri':'http://127.0.0.1:5176/demo-api/auth/callback'},synthetic=True)

def sign_in(client,role):
  start=client.post('/demo-api/auth/start',json={}).json()['url']
  authorized=client.get(start+'&demo_role='+role,follow_redirects=False)
  callback=authorized.headers['location']
  result=client.get(callback,follow_redirects=False)
  assert result.status_code==303 and result.headers['location']=='/'
  return callback

def test_viewer_cannot_mutate_and_state_is_single_use(tmp_path):
  with TestClient(create_app(tmp_path,seed=False,identity=synthetic()),base_url='http://127.0.0.1:5176') as c:
    c.headers.update(HEADERS)
    callback=sign_in(c,'viewer')
    principal=c.get('/demo-api/session').json()
    assert principal['role']=='viewer' and principal['authentication']=='synthetic_entra'
    for path in ('overview','audit','events','policy','network'):
      assert c.get('/demo-api/'+path).status_code==200
    for path in ('policy','policy/validate','network','network/validate','password','scenarios/read'):
      assert c.post('/demo-api/'+path,json={}).status_code==403
    assert c.get(callback).status_code==400
    assert c.post('/demo-api/logout',json={}).status_code==200
    assert c.get('/demo-api/session').status_code==401

def test_admin_policy_and_attributed_audit(tmp_path):
  with TestClient(create_app(tmp_path,seed=False,identity=synthetic()),base_url='http://127.0.0.1:5176') as c:
    c.headers.update(HEADERS);sign_in(c,'admin')
    policy=c.get('/demo-api/policy').json()
    assert c.post('/demo-api/policy',json=policy).status_code==200
    assert c.post('/demo-api/password',json={'current_password':'1234','new_password':'Changed1234'}).status_code==403
    assert any(r['actor']==TENANT+'/synthetic-admin' and r['event']=='console.write' for r in c.get('/demo-api/audit').json())

def test_callback_rejects_other_browser(tmp_path):
  app=create_app(tmp_path,seed=False,identity=synthetic())
  with TestClient(app,base_url='http://127.0.0.1:5176') as first, TestClient(app,base_url='http://127.0.0.1:5176') as other:
    first.headers.update(HEADERS)
    url=first.post('/demo-api/auth/start',json={}).json()['url']
    callback=first.get(url+'&demo_role=admin',follow_redirects=False).headers['location']
    assert other.get(callback).status_code==400
    assert first.get(callback,follow_redirects=False).status_code==303

def test_real_config_disables_synthetic_routes_and_local_optout(tmp_path,identity):
  with TestClient(create_app(tmp_path,seed=False,identity=identity,local_login=False)) as c:
    c.headers.update(HEADERS)
    assert c.get('/demo-api/auth/config').json()=={'enabled':True,'synthetic':False,'local_login':False}
    assert c.post('/demo-api/login',json={'username':'admin','password':'1234'}).status_code==403
    assert c.get('/demo-api/auth/synthetic/authorize').status_code==404
    assert c.post('/demo-api/auth/start',json={},headers={'origin':'https://evil.test'}).status_code==403

def test_real_exchange_posts_pkce_and_validates_token(identity,key,monkeypatch):
  import httpx
  from types import SimpleNamespace
  original=httpx.Client
  def endpoint(request):
    assert str(request.url)==f'https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token'
    form=parse_qs(request.content.decode())
    assert form['code_verifier']==['verifier'] and form['client_secret']==['test-only']
    assert form['redirect_uri']==[identity.redirect]
    return httpx.Response(200,json={'id_token':token(key)})
  monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(endpoint),**kw))
  monkeypatch.setattr(identity.keys,'get_signing_key_from_jwt',lambda encoded:SimpleNamespace(key=key.public_key()))
  assert identity.exchange('code','verifier','nonce')['role']=='viewer'
  with pytest.raises(IdentityError):identity.exchange('code','verifier','wrong-nonce')

def test_existing_synthetic_session_rejected_by_real_mode(tmp_path,identity):
  with TestClient(create_app(tmp_path,seed=False,identity=synthetic()),base_url='http://127.0.0.1:5176') as c:
    c.headers.update(HEADERS);sign_in(c,'admin');cookie=c.cookies.get('td_demo_session')
  with TestClient(create_app(tmp_path,seed=False,identity=identity)) as real:
    real.cookies.set('td_demo_session',cookie)
    assert real.get('/demo-api/session').status_code==401

@pytest.mark.parametrize('redirect',['http://evil.test/demo-api/auth/callback','https://console.test/other','https://console.test/demo-api/auth/callback?next=evil'])
def test_config_rejects_unsafe_callback(redirect):
  with pytest.raises(IdentityError):Identity({'tenant_id':TENANT,'client_id':CLIENT,'client_secret':'secret','redirect_uri':redirect})
