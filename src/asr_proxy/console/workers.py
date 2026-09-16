"""Supervised same-host console workers sharing versioned policy and decision state."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import grpc
import uvicorn
from fastapi import FastAPI
from envoy.service.ext_proc.v3 import external_processor_pb2_grpc as rpc

from asr_proxy.inspection.pool import InspectorPool, atomic_write, parser as pool_parser
from asr_proxy.inspection.server import watch_parent


class ConsolePool(InspectorPool):
  def spawn(self, index, restarts=0):
    fd=os.open(self.state / f'inspector-{index}.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'ab') as log:
      process=subprocess.Popen([sys.executable,'-m','asr_proxy.console.workers','worker',
        '--directory',self.args.directory,'--key-file',str(self.snapshot/'key'),
        '--grpc-port',str(self.grpc_ports[index]),'--health-port',str(self.health_ports[index]),
        '--parent-pid',str(os.getpid())],stdout=log,stderr=subprocess.STDOUT)
    return {'process':process,'restarts':restarts,'state':'starting','started':time.monotonic(),
            'misses':0,'retry_at':None}

  def healthy(self,index):
    if os.getppid()!=self.args.parent_pid:self.stop()
    return super().healthy(index)


async def worker(args):
  from .runtime import Runtime
  from .dataplane import ConsoleProcessor
  if os.getppid()!=args.parent_pid:raise RuntimeError('console_parent_unavailable')
  runtime=Runtime(args.directory)
  runtime.key=Path(args.key_file).read_bytes()
  runtime.configure(runtime.policy())
  server=grpc.aio.server(maximum_concurrent_rpcs=32)
  rpc.add_ExternalProcessorServicer_to_server(ConsoleProcessor(runtime),server)
  if not server.add_insecure_port(f'127.0.0.1:{args.grpc_port}'):raise RuntimeError('grpc_bind_failed')
  await server.start()
  app=FastAPI()
  @app.get('/_trapdefense/health')
  def health():return {'status':'ok'}
  web=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.health_port,
    access_log=False,timeout_graceful_shutdown=3))
  watcher=asyncio.create_task(watch_parent(web,args.parent_pid))
  try:await web.serve()
  finally:
    watcher.cancel()
    await asyncio.gather(watcher,return_exceptions=True)
    await server.stop(2)


class WorkerManager:
  def __init__(self,runtime):
    self.runtime=runtime
    self.directory=runtime.store.directory.resolve()/'inspectors'
    self.process=None

  def status(self):
    process=self.process
    if process is None:return {'state':'stopped','replicas':[]}
    try:result=json.loads((self.directory/'status.json').read_text())
    except (OSError,ValueError):return {'state':'starting' if process.poll() is None else 'failed','replicas':[]}
    if process.poll() is not None or result.get('supervisor_pid')!=process.pid:
      result['state']='failed'
    elif time.time()-result.get('updated_at',0)>10:result['state']='unresponsive'
    if result['state'] in ('failed','unresponsive'):
      for member in result.get('replicas',[]):member['state']='unknown'
    return result

  def start(self,replicas):
    import yaml
    if self.process and self.process.poll() is None:raise ValueError('Inspector pool is already running')
    self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    atomic_write(self.directory/'input.yaml',yaml.safe_dump(self.runtime.config(self.runtime.policy()).model_dump()))
    atomic_write(self.directory/'key',self.runtime.key)
    fd=os.open(self.directory/'supervisor.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'ab') as log:
      self.process=subprocess.Popen([sys.executable,'-m','asr_proxy.console.workers','pool',
        '--directory',str(self.runtime.store.directory.resolve()),'--parent-pid',str(os.getpid()),
        '--config',str(self.directory/'input.yaml'),'--key-file',str(self.directory/'key'),
        '--state-directory',str(self.directory),'--envoy-output',str(self.directory/'envoy.yaml'),
        '--replicas',str(replicas)],stdout=log,stderr=subprocess.STDOUT)
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
      if self.status()['state']=='healthy':return
      if self.process.poll() is not None:break
      time.sleep(.1)
    self.stop()
    raise ValueError('Inspector pool did not become ready; check private inspector logs')

  def stop(self):
    if self.process and self.process.poll() is None:
      self.process.terminate()
      try:self.process.wait(timeout=15)
      except subprocess.TimeoutExpired:
        self.process.kill();self.process.wait(timeout=3)
    self.process=None


def main():
  mode=sys.argv[1]
  if mode=='worker':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',required=True)
    parser.add_argument('--key-file',required=True)
    parser.add_argument('--grpc-port',type=int,required=True)
    parser.add_argument('--health-port',type=int,required=True)
    parser.add_argument('--parent-pid',type=int,required=True)
    asyncio.run(worker(parser.parse_args(sys.argv[2:])))
  elif mode=='pool':
    parser=pool_parser()
    parser.add_argument('--directory',required=True)
    parser.add_argument('--parent-pid',type=int,required=True)
    args=parser.parse_args(sys.argv[2:])
    if os.getppid()!=args.parent_pid:raise RuntimeError('console_parent_unavailable')
    pool=ConsolePool(args)
    signal.signal(signal.SIGTERM,pool.stop)
    signal.signal(signal.SIGINT,pool.stop)
    try:pool.run()
    finally:pool.client.close()
  else:raise ValueError('Unknown worker mode')


if __name__=='__main__':main()
