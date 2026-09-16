"""Management runtime which sends actual network traffic; no engine-only fallback."""
import asyncio
import json
import threading
import time
from dataclasses import replace
from uuid import uuid4

import grpc
import httpx
from envoy.service.ext_proc.v3 import external_processor_pb2_grpc as rpc
from asr_proxy.inspection.contracts import HttpMessage
from asr_proxy.inspection.identity import sign_attestation
from .store import Store
from .scenarios import Policy, CASES, TOOLS
from threading import RLock
import secrets
from asr_proxy.inspection.contracts import InspectionConfig
from asr_proxy.inspection.engine import InspectionEngine
from asr_proxy.inspection.identity import AttestationVerifier
from asr_proxy.inspection.pii import PresidioScanner
from .network import NetworkManager
from .dataplane import ConsoleProcessor
from .destination import create_destination


class Runtime:
  integrated=True
  def __init__(self,directory,seed=False):
    self.store=Store(directory)
    self.lock=RLock()
    self.key=secrets.token_bytes(48)
    self.scanner=PresidioScanner()
    if self.store.get('policy') is None:self.store.set('policy',Policy().model_dump())
    self.network=NetworkManager(self.store)
    self.configure(self.policy())
    self.grpc_server=None
    self.destination=None
    self.inspector_ready=False

  def config(self,policy):
    if set(policy['rules'])!=set(TOOLS):raise ValueError('Every mapped tool must have an explicit rule')
    config=InspectionConfig(edition='community',trusted_sources=['demo-decryptor'],pii_action=policy['pii_action'],
      nonce_db=str(self.store.directory/'nonces.sqlite'),audit_path=str(self.store.directory/'inspection.jsonl'),
      routes=[{'authority':'tools.demo.test','path':'/mcp','tools':{name:{'action':action,'resource':resource,'effect':policy['rules'][name]} for name,(action,resource) in TOOLS.items()},'redact_fields':['/params/arguments/message']}])
    network=self.store.get('network')
    if network:config.max_body_bytes=network['max_body_bytes']
    return config

  def policy(self):return Policy.model_validate(self.store.get('policy')).model_dump()

  def build_engine(self,policy):
    config=self.config(policy)
    verifier=AttestationVerifier(self.key,config.nonce_db,required_fields=('source_id',))
    return InspectionEngine(config,self.scanner,verifier,None)

  def configure(self,policy):self.engine=self.build_engine(policy)

  def apply(self,payload):
    with self.lock:
      candidate=Policy.model_validate(payload).model_dump()
      self.config(candidate)
      if candidate['version']!=self.policy()['version']:raise ValueError('Policy changed; refresh before applying')
      candidate['version']+=1
      engine=self.build_engine(candidate)
      self.store.save_policy(candidate)
      self.engine=engine
      return candidate

  async def start(self):
    self.destination=create_destination()
    self.destination_thread=threading.Thread(target=self.destination.serve_forever,daemon=True)
    self.destination_thread.start()
    self.grpc_server=grpc.aio.server()
    rpc.add_ExternalProcessorServicer_to_server(ConsoleProcessor(self),self.grpc_server)
    if not self.grpc_server.add_insecure_port('127.0.0.1:18081'):raise RuntimeError('Inspector port unavailable')
    await self.grpc_server.start()
    self.inspector_ready=True
    try:await asyncio.to_thread(self.network.start)
    except Exception:
      await self.stop()
      raise
    self.store.audit('installation.started','Envoy + gRPC inspector + synthetic HTTP destination')

  async def stop(self):
    await asyncio.to_thread(self.network.stop)
    self.inspector_ready=False
    if self.grpc_server:await self.grpc_server.stop(1)
    if self.destination:
      await asyncio.to_thread(self.destination.shutdown)
      self.destination.server_close()

  def update_network(self,payload):
    # No traffic generator runs across a listener replacement.
    with self.network.lock:
      result=self.network.apply(payload)
      with self.lock:self.configure(self.policy())
      return result

  def network_status(self):
    result=self.network.status()
    result['inspector_ready']=self.inspector_ready
    try:
      with httpx.Client(timeout=.5,trust_env=False) as c:
        response=c.get('http://127.0.0.1:18090/_demo/stats')
      result['destination_ready']=response.status_code==200
      result['destination_count']=response.json().get('count',0)
    except (httpx.HTTPError,ValueError):result['destination_ready']=False
    return result

  def signed_request(self,client,name):
    case=CASES[name]
    arguments={'message':case['message']}
    if name=='response':arguments['demo_response_pii']=True
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':case['tool'],'arguments':arguments}}).encode()
    port=self.network.current()['listen_port']
    request=client.build_request('POST',f'http://127.0.0.1:{port}/mcp',
      headers={'host':'tools.demo.test','content-type':'application/json'},content=body)
    message=HttpMessage('POST','tools.demo.test','/mcp',dict(request.headers),body)
    run_id=uuid4().hex
    identity={'source_id':'demo-decryptor','agent_id':case['agent'],'scenario':name,'run_id':run_id}
    request.headers['x-td-attestation']=sign_attestation(message,identity,self.key,nonce=uuid4().hex)
    return request,run_id

  def run(self,name,**kwargs):
    with self.network.lock:
      started=time.perf_counter()
      with httpx.Client(timeout=35,trust_env=False,follow_redirects=False) as client:
        request,run_id=self.signed_request(client,name)
        try:response=client.send(request)
        except httpx.HTTPError:
          self.store.audit('proxy.transport_failed',f'{name} · proxy unavailable; no direct fallback')
          raise ValueError('Proxy connection failed. Check Connections / System.') from None
      event=None
      for _ in range(50):
        event=next((e for e in self.store.events() if e.get('transport',{}).get('run_id')==run_id),None)
        if event:break
        time.sleep(.02)
      if event is None:
        self.store.audit('proxy.evidence_missing',f'{name} · HTTP {response.status_code}')
        raise ValueError(f'Proxy HTTP {response.status_code}: inspection evidence is missing; no direct-engine fallback was used.')
      receipt=None
      try:
        body=response.json()
        raw=body.get('receipt')
        if isinstance(raw,dict) and self.destination and raw.get('id') in self.destination.receipts:
          receipt=self.destination.receipts[raw['id']]
      except ValueError:body={}
      event['transport'].update(http_status=response.status_code,round_trip_ms=round((time.perf_counter()-started)*1000,2),
        receipt=receipt,response_redacted='[REDACTED]' in response.text)
      self.store.update_event(event)
      self.store.audit('proxy.scenario_completed',f'{name} → HTTP {response.status_code} · {event["action"]} · event {event["id"]}')
      return event
