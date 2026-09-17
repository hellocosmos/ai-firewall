"""Opt-in real pool, Envoy, process failure and replay persistence checks."""
import contextlib
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import yaml

from asr_proxy.inspection.demo import init_demo
from firewall_support import destination, signed_request, tool_body
from test_dataplane_transport import docker_command, free_port
from asr_proxy.console.network import IMAGE

pytestmark = pytest.mark.skipif(os.environ.get('TD_RUNTIME_SMOKE') != '1', reason='opt-in real runtime')


def wait_for(callback, seconds=15):
  deadline = time.monotonic()+seconds
  while time.monotonic()<deadline:
    value = callback()
    if value: return value
    time.sleep(.1)
  raise AssertionError('runtime condition did not become true')


def contiguous(count):
  for _ in range(100):
    base = free_port(); sockets=[]
    try:
      for port in range(base, base+count):
        s=socket.socket(); sockets.append(s); s.bind(('127.0.0.1',port))
      return base
    except OSError: pass
    finally:
      for s in sockets: s.close()
  raise AssertionError('no free port range')


@contextlib.contextmanager
def pool_fixture(tmp_path, count=2, restarts=3, upstream=18090):
  init_demo(tmp_path/'demo')
  grpc = contiguous(2 * count + 1)
  health, proxy = grpc + count, grpc + 2 * count
  state=tmp_path/'pool'; output=tmp_path/'envoy.yaml'
  log=(tmp_path/'pool.log').open('wb')
  process=subprocess.Popen([sys.executable,'-m','asr_proxy.inspection.pool',
    '--config',str(tmp_path/'demo/inspector.yaml'),'--key-file',str(tmp_path/'demo/attestation.key'),
    '--state-directory',str(state),'--envoy-output',str(output),'--replicas',str(count),
    '--grpc-base-port',str(grpc),'--health-base-port',str(health),'--proxy-port',str(proxy),
    '--upstream-port',str(upstream),'--max-restarts',str(restarts),
    '--proxy-bind','127.0.0.1' if platform.system()=='Linux' else '0.0.0.0',
    '--inspector-address','127.0.0.1' if platform.system()=='Linux' else 'host.docker.internal',
    '--upstream-address','127.0.0.1' if platform.system()=='Linux' else 'host.docker.internal'],stdout=log,stderr=subprocess.STDOUT)
  def status():
    path=state/'status.json'
    return json.loads(path.read_text()) if path.exists() else {}
  try:
    wait_for(lambda: status().get('state')=='healthy')
    yield {'process':process,'status':status,'output':output,'port':proxy,
           'key':(tmp_path/'demo/attestation.key').read_bytes()}
  finally:
    if process.poll() is None: process.terminate()
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired: process.kill();process.wait(timeout=2)
    log.close()


@contextlib.contextmanager
def envoy(pool):
  name=f'td-pool-test-{os.getpid()}-{pool["port"]}'
  command=['docker'] if platform.system()=='Linux' else docker_command()
  network=['--network','host'] if platform.system()=='Linux' else ['--publish',f'127.0.0.1:{pool["port"]}:{pool["port"]}']
  subprocess.run(command+['run','-d','--rm','--pull=never','--name',name,
    '--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532',
    *network,
    '--mount',f'type=bind,source={pool["output"]},target=/etc/envoy/pool.yaml,readonly',
    '--entrypoint','/usr/local/bin/envoy',IMAGE,'--concurrency','2','-c','/etc/envoy/pool.yaml'],
    check=True,capture_output=True)
  try:
    # Allow active endpoint health checks; readiness itself does not send tool calls.
    def ready():
      try:
        with socket.create_connection(('127.0.0.1',pool['port']),timeout=.2): return True
      except OSError:return False
    wait_for(ready);time.sleep(1.5)
    yield
  finally: subprocess.run(command+['stop','--time','1',name],capture_output=True,check=False)


@pytest.mark.parametrize('count',[1,4])
def test_pool_choices_start_and_parent_death_stops_children(tmp_path,count):
  with pool_fixture(tmp_path,count=count) as pool:
    members=pool['status']()['replicas']
    assert len(members)==count
    pool['process'].kill();pool['process'].wait(timeout=2)
    def closed():
      for m in members:
        try:
          with socket.create_connection(('127.0.0.1',m['grpc_port']),timeout=.2):return False
        except OSError:pass
      return True
    wait_for(closed)


def test_pool_restarts_preserve_replay_and_all_down_fails_closed(tmp_path):
  with destination() as (upstream,received), pool_fixture(tmp_path,upstream=upstream) as pool, envoy(pool):
    rendered = pool['output'].read_bytes()
    duplicate = subprocess.run(pool['process'].args, capture_output=True, text=True, timeout=5)
    assert duplicate.returncode == 1 and 'pool_already_running' in duplicate.stderr
    assert pool['output'].read_bytes() == rendered
    assert pool['status']()['supervisor_pid'] == pool['process'].pid
    with httpx.Client(timeout=8,trust_env=False) as client:
      request=signed_request(client,pool['port'],pool['key'])
      token=request.headers['x-td-attestation']
      assert client.send(request).status_code==200
      assert client.send(signed_request(client,pool['port'],pool['key'],body=tool_body('alex@example.com'))).status_code==200
      assert b'alex@example.com' not in received[-1]['body']
      assert client.send(signed_request(client,pool['port'],pool['key'],body=tool_body(tool='notes.delete'))).status_code==403
      config_path=tmp_path/'demo/inspector.yaml'
      changed=yaml.safe_load(config_path.read_text())
      changed['routes'][0]['tools']['notes.read']['effect']='block'
      config_path.write_text(yaml.safe_dump(changed))
      (tmp_path/'demo/attestation.key').write_bytes(b'rotated-synthetic-key-only-' * 2)
      old=pool['status']()['replicas'][0]['pid'];os.kill(old,signal.SIGKILL)
      wait_for(lambda: pool['status']().get('state')=='healthy' and pool['status']()['replicas'][0]['pid']!=old)
      time.sleep(1.5)  # Let Envoy re-admit the recovered endpoint after its health check.
      for _ in range(6):
        assert client.send(signed_request(client,pool['port'],pool['key'])).status_code==200
      for _ in range(6):
        replay=signed_request(client,pool['port'],pool['key']);replay.headers['x-td-attestation']=token
        response=client.send(replay)
        assert response.status_code==403
      assert len(received)==8
      pool['process'].terminate();pool['process'].wait(timeout=10)
      response=client.send(signed_request(client,pool['port'],pool['key']))
      assert response.status_code>=500 and len(received)==8


def test_exhausted_recovery_stops_entire_pool(tmp_path):
  with pool_fixture(tmp_path,restarts=0) as pool:
    old=pool['status']()['replicas'][0]['pid'];os.kill(old,signal.SIGKILL)
    assert pool['process'].wait(timeout=12)==1
    assert pool['status']()['state']=='failed'
    assert all(m['state']=='stopped' for m in pool['status']()['replicas'])
