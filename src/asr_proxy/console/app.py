"""Loopback-only demo service. Never attached to the production API application."""
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI,APIRouter,Depends,HTTPException,Request,Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field

from .runtime import Runtime
from .scenarios import Policy,CASES

COOKIE='td_demo_session'
ORIGINS={'http://127.0.0.1:5176','http://localhost:5176'}

class Login(BaseModel):
  username:str=Field(min_length=1,max_length=80)
  password:str=Field(min_length=1,max_length=128)
class Password(BaseModel):
  current_password:str=Field(min_length=1,max_length=128)
  new_password:str=Field(min_length=8,max_length=128)
class Run(BaseModel):
  model_config=ConfigDict(extra='forbid')



def create_app(directory,seed=True,*,runtime_factory=Runtime,lifespan=None):
  runtime=runtime_factory(directory,seed=seed)
  app=FastAPI(title='TrapDefense Community Console',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
  app.state.runtime=runtime

  @app.middleware('http')
  async def boundaries(request,call_next):
    # Reject cross-origin writes, including login CSRF; no permissive CORS middleware.
    if request.method not in ('GET','HEAD','OPTIONS'):
      if request.headers.get('origin') not in ORIGINS or request.headers.get('x-td-demo')!='1':
        return JSONResponse({'detail':'Cross-origin or missing CSRF request rejected'},status_code=403)
      if request.headers.get('content-type','').split(';')[0]!='application/json':
        return JSONResponse({'detail':'JSON required'},status_code=415)
      size=0
      chunks=[]
      async for chunk in request.stream():
        size+=len(chunk)
        if size>16384:return JSONResponse({'detail':'Request too large'},status_code=413)
        chunks.append(chunk)
      request._body=b''.join(chunks)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

  @app.exception_handler(ValueError)
  async def invalid(request,exc):return JSONResponse({'detail':str(exc)},status_code=400)

  @app.exception_handler(RequestValidationError)
  async def validation(request,exc):
    # Never echo invalid password or arbitrary request input from Pydantic errors.
    return JSONResponse({'detail':'Check the format and length of the input.'},status_code=422)

  def authenticated(request:Request):
    if not runtime.store.authenticated(request.cookies.get(COOKIE)):raise HTTPException(401,'Sign in to continue.')
    return 'admin'

  @app.get('/demo-api/health')
  def health():return {'status':'ready','synthetic':True,'integrated':getattr(runtime,'integrated',False)}

  @app.post('/demo-api/login')
  def login(payload:Login,request:Request,response:Response):
    with runtime.lock:
      identity='local-admin'
      if runtime.store.login_attempt(identity):raise HTTPException(429,'Too many login attempts. Try again in 60 seconds.')
      valid=runtime.store.check_password(payload.password) and payload.username=='admin'
      runtime.store.login_attempt(identity,valid)
      if not valid:
        runtime.store.audit('account.login_failed','Invalid local credential',actor='anonymous')
        raise HTTPException(401,'Incorrect username or password.')
      runtime.store.logout(request.cookies.get(COOKIE))
      token=runtime.store.create_session()
      response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=False,path='/demo-api',max_age=8*3600)
      runtime.store.audit('account.login','Local demo session started')
      return {'username':'admin','password_changed':runtime.store.changed()}

  router=APIRouter(prefix='/demo-api',dependencies=[Depends(authenticated)])

  @router.get('/session')
  def session():return {'username':'admin','password_changed':runtime.store.changed()}

  @router.post('/logout')
  def logout(request:Request,response:Response):
    runtime.store.logout(request.cookies.get(COOKIE));response.delete_cookie(COOKIE,path='/demo-api')
    runtime.store.audit('account.logout','Local session ended')
    return {'ok':True}

  @router.post('/password')
  def password(payload:Password,response:Response):
    if payload.current_password==payload.new_password:raise HTTPException(400,'The new password must differ from the current password.')
    if not runtime.store.change_password(payload.current_password,payload.new_password):raise HTTPException(400,'The current password is incorrect.')
    response.delete_cookie(COOKIE,path='/demo-api')
    return {'ok':True,'reauthenticate':True}

  @router.get('/overview')
  def overview():
    network=runtime.network_status() if getattr(runtime,'integrated',False) else None
    return {'events':runtime.store.events(),'broker':{'agents':[],'delegations':[],'approvals':[]},'edition':'community','capabilities':{'broker':False},'policy':runtime.policy(),
      'scenarios':[{'id':key,'label':value['label']} for key,value in CASES.items()],
      'system':{'inspector':('ready' if network and network['inspector_ready'] else 'unavailable'),'broker':'not_included','database':'ready','proxy':('ready' if network['proxy_ready'] else 'unavailable') if network else 'not_connected','iam':'synthetic','tls':'synthetic'},'synthetic':True,'integrated':getattr(runtime,'integrated',False),
      'network':network}

  @router.get('/events')
  def events():return runtime.store.events()

  @router.get('/audit')
  def audit():return runtime.store.audits()

  @router.get('/policy')
  def policy():return runtime.policy()

  @router.post('/policy/validate')
  def validate(payload:Policy):
    runtime.config(payload.model_dump())
    return {'valid':True,'scope':'local-demo'}

  @router.post('/policy')
  def apply(payload:Policy):return runtime.apply(payload.model_dump())

  @router.post('/scenarios/{name}')
  def scenario(name:str,payload:Run):
    if name not in CASES:raise HTTPException(404,'Scenario not found')
    return runtime.run(name)

  if getattr(runtime,'integrated',False):
    from .network import NetworkConfig
    @router.get('/network')
    def network_status():return runtime.network_status()
    @router.post('/network/validate')
    def validate_network(payload:NetworkConfig):
      runtime.network.validate(payload.model_dump())
      return {'valid':True}
    @router.post('/network')
    def apply_network(payload:NetworkConfig):return runtime.update_network(payload.model_dump())

  app.include_router(router)
  return app

from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifecycle(app):
  await app.state.runtime.start()
  try:yield
  finally:await app.state.runtime.stop()


def from_env():
  repository=Path(__file__).resolve().parents[3]
  directory=Path(os.environ.get('TD_CONSOLE_STATE',str(repository/'.runtime-state/console')))
  assets=Path(os.environ.get('TD_CONSOLE_ASSETS',str(repository/'console/dist')))
  if not (assets/'index.html').is_file():raise RuntimeError('Build console assets with scripts/install-console.sh')
  app=create_app(directory,seed=False,lifespan=lifecycle)
  app.mount('/',StaticFiles(directory=assets,html=True),name='console')
  return app


def main():
  import argparse
  import uvicorn
  parser=argparse.ArgumentParser(description='Run the local Community proxy console (requires Docker)')
  parser.add_argument('--state-dir',help='Persistent local console state directory')
  parser.add_argument('--assets',help='Built console/dist directory')
  args=parser.parse_args()
  if args.state_dir:os.environ['TD_CONSOLE_STATE']=args.state_dir
  if args.assets:os.environ['TD_CONSOLE_ASSETS']=args.assets
  uvicorn.run('asr_proxy.console.app:from_env',factory=True,host='127.0.0.1',port=5176,access_log=False,ws='none')
