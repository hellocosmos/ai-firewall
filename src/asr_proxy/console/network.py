"""Versioned, loopback-only Envoy installation. Never changes host NICs or routes."""
import hashlib
import json
import platform
import socket
import subprocess
import time
from pathlib import Path
from threading import RLock
from typing import Literal

import httpx
import psutil
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

IMAGE='envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4'
ENVOY_TEMPLATE=Path(__file__).with_name('envoy-inline.yaml')


class NetworkConfig(BaseModel):
  model_config=ConfigDict(extra='forbid')
  version:int=Field(default=1,ge=1)
  topology:Literal['explicit_loopback']='explicit_loopback'
  listen_address:Literal['127.0.0.1']='127.0.0.1'
  listen_port:int=Field(default=18082,ge=1024,le=65535)
  request_timeout:int=Field(default=5,ge=2,le=30)
  max_body_bytes:int=Field(default=1048576,ge=1024,le=1048576)

  @model_validator(mode='after')
  def reserved(self):
    if self.listen_port in {5176,5186,8181,8191,18081,18090,18101,18102,18103,18104,18111,18112,18113,18114}:
      raise ValueError('Port is reserved for management, inspection or destination')
    return self


def inventory():
  stats=psutil.net_if_stats()
  result=[]
  for name,addresses in psutil.net_if_addrs().items():
    ips=[a.address for a in addresses if a.family in (socket.AF_INET,socket.AF_INET6)]
    loopback=any(a=='127.0.0.1' for a in ips)
    state=stats.get(name)
    result.append({'name':name,'addresses':ips,'up':bool(state and state.isup),
      'mtu':state.mtu if state else None,'kind':'loopback' if loopback else 'host interface',
      'role':'Management / proxy ingress / synthetic destination' if loopback else 'Not bound by this installation'})
  return result


class NetworkManager:
  def __init__(self,store):
    self.store=store
    self.lock=RLock()
    suffix=hashlib.sha256(str(store.directory.resolve()).encode()).hexdigest()[:12]
    self.name='trapdefense-console-'+suffix
    self.label='com.trapdefense.console='+suffix
    self.linux=platform.system()=='Linux'
    self.last_error=None
    self.running=False
    self.replicas=(store.get('inspectors') or {'replicas':1})['replicas']
    if store.get('network') is None:store.set('network',NetworkConfig().model_dump())

  def current(self):return NetworkConfig.model_validate(self.store.get('network')).model_dump()

  def render(self,config):
    from asr_proxy.inspection.pool import parser, render_envoy
    args=parser().parse_args(['--config','unused','--key-file','unused',
      '--state-directory','unused','--envoy-output','unused','--replicas',str(self.replicas),
      '--proxy-port',str(config.listen_port),'--inspector-address',
      '127.0.0.1' if self.linux else 'host.docker.internal'])
    value=render_envoy(args)
    listener=value['static_resources']['listeners'][0]
    listener['address']['socket_address']={'address':'127.0.0.1' if self.linux else '0.0.0.0','port_value':config.listen_port}
    listener['per_connection_buffer_limit_bytes']=config.max_body_bytes
    hcm=listener['filter_chains'][0]['filters'][0]['typed_config']
    hcm['request_timeout']=hcm['stream_idle_timeout']=f'{config.request_timeout}s'
    hcm['generate_request_id']=False
    route=hcm['route_config']['virtual_hosts'][0]['routes'][0]
    route['route']['timeout']=f'{config.request_timeout}s'
    route['route']['max_stream_duration']['max_stream_duration']=f'{config.request_timeout}s'
    hcm['route_config']['virtual_hosts'][0]['routes'].insert(0,{
      'match':{'path':'/__td_ready','headers':[{'name':':method','string_match':{'exact':'GET'}}]},
      'direct_response':{'status':200,'body':{'inline_string':f'td-console-v{config.version}'}},
      'typed_per_filter_config':{'envoy.filters.http.ext_proc':{
        '@type':'type.googleapis.com/envoy.extensions.filters.http.ext_proc.v3.ExtProcPerRoute','disabled':True}}})
    for cluster in value['static_resources']['clusters']:
      address=cluster['load_assignment']['endpoints'][0]['lb_endpoints'][0]['endpoint']['address']['socket_address']
      address['address']='127.0.0.1' if self.linux else 'host.docker.internal'
    return value

  def command(self,*args,timeout=20,check=True):
    result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout)
    if check and result.returncode:raise ValueError('Envoy Docker operation failed; previous configuration is retained when possible')
    return result

  def config_file(self,config):
    digest=hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:12]
    path=self.store.directory/f'envoy-v{config.version}-{digest}.yaml'
    path.write_text(yaml.safe_dump(self.render(config)))
    path.chmod(0o644) # No keys; unprivileged Envoy needs read access inside its mount.
    return path.resolve()

  def validate(self,payload):
    config=NetworkConfig.model_validate(payload)
    path=self.config_file(config)
    self.command('run','--rm','--pull=never','--network','none','--read-only','--cap-drop=ALL',
      '--security-opt=no-new-privileges','--user','65532:65532','--entrypoint','/usr/local/bin/envoy',
      '--mount',f'type=bind,source={path},target=/etc/envoy/console.yaml,readonly',IMAGE,
      '--mode','validate','-c','/etc/envoy/console.yaml',timeout=30)
    return config

  def stop(self):
    found=self.command('inspect',self.name,check=False)
    if found.returncode:return
    labels=json.loads(found.stdout)[0]['Config'].get('Labels') or {}
    key,value=self.label.split('=',1)
    if labels.get(key)!=value:raise ValueError('Container name belongs to another installation')
    self.command('rm','-f',self.name)
    self.running=False

  def launch(self,config):
    path=self.config_file(config)
    args=['run','-d','--pull=never','--name',self.name,'--label',self.label,'--read-only',
      '--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532',
      '--entrypoint','/usr/local/bin/envoy']
    args+=['--network','host'] if self.linux else ['--publish',f'127.0.0.1:{config.listen_port}:{config.listen_port}']
    self.command(*args,'--mount',f'type=bind,source={path},target=/etc/envoy/console.yaml,readonly',
      IMAGE,'--concurrency','2','--log-level','error','-c','/etc/envoy/console.yaml')
    for _ in range(40):
      if self.probe(config):self.running=True;return
      time.sleep(.1)
    raise ValueError('New Envoy listener did not become ready')

  def probe(self,config=None):
    config=config or NetworkConfig.model_validate(self.current())
    try:
      with httpx.Client(timeout=.5,trust_env=False) as client:
        response=client.get(f'http://127.0.0.1:{config.listen_port}/__td_ready')
      return response.status_code==200 and response.text==f'td-console-v{config.version}'
    except httpx.HTTPError:return False

  def start(self):
    with self.lock:
      config=self.validate(self.current())
      self.stop()
      try:self.launch(config)
      except Exception:
        self.stop()
        raise

  def apply(self,payload):
    with self.lock:
      previous=NetworkConfig.model_validate(self.current())
      draft=NetworkConfig.model_validate(payload)
      if draft.version!=previous.version:raise ValueError('Network configuration changed; refresh before applying')
      candidate=draft.model_copy(update={'version':previous.version+1})
      candidate=self.validate(candidate)
      self.store.audit('network.applying',f'v{candidate.version} · port {candidate.listen_port}')
      self.stop()
      try:
        self.launch(candidate)
        self.store.set('network',candidate.model_dump())
      except Exception:
        self.stop()
        try:self.launch(previous)
        except Exception:
          self.last_error='Apply failed and rollback listener is unavailable'
          self.store.audit('network.rollback_failed',self.last_error)
          raise ValueError(self.last_error) from None
        self.last_error='Apply failed; previous listener restored'
        self.store.audit('network.rolled_back',self.last_error)
        raise ValueError(self.last_error) from None
      self.last_error=None
      self.store.audit('network.applied',f'v{candidate.version} · 127.0.0.1:{candidate.listen_port}')
      return self.status()

  def status(self):
    return {'applied':self.current(),'interfaces':inventory(),'proxy_ready':self.probe(),
      'last_error':self.last_error,'host_os':platform.system(),'container':self.name,
      'inspector_endpoint':f'127.0.0.1:18101–{18100+self.replicas} (gRPC)', 'upstream_endpoint':'127.0.0.1:18090 (synthetic HTTP)',
      'supported_topologies':['explicit_loopback'],'unavailable_topologies':['dual_nic_routed','transparent_bridge'],
      'egress_binding':'OS route / Docker host forwarding; no physical NIC pinning',
      'tls':'External decryptor not connected; trusted-hop simulator signs plaintext synthetic input'}
