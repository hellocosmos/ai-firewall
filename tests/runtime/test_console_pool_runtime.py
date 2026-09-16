"""Console policy, events and recovery through actual Envoy."""
import os
import platform
import signal
import threading
import time
import httpx
import pytest
import yaml
from asr_proxy.console.runtime import Runtime
from asr_proxy.console.destination import create_destination
from asr_proxy.inspection.pool import parser,render_envoy
from test_inspector_pool_runtime import envoy,wait_for
from test_dataplane_transport import free_port
pytestmark=pytest.mark.skipif(os.environ.get('TD_RUNTIME_SMOKE')!='1',reason='opt-in real runtime')


def test_console_pool_policy_events_recovery_and_stop(tmp_path):
  runtime=Runtime(tmp_path/'console');destination=create_destination(0)
  threading.Thread(target=destination.serve_forever,daemon=True).start()
  runtime.destination=destination;port=free_port()
  network=runtime.network.current();network['listen_port']=port;runtime.store.set('network',network)
  args=parser().parse_args(['--config','unused','--key-file','unused','--state-directory','unused',
    '--envoy-output','unused','--replicas','2','--proxy-port',str(port),
    '--proxy-bind','127.0.0.1' if platform.system()=='Linux' else '0.0.0.0',
    '--inspector-address','127.0.0.1' if platform.system()=='Linux' else 'host.docker.internal',
    '--upstream-address','127.0.0.1' if platform.system()=='Linux' else 'host.docker.internal','--upstream-port',str(destination.server_port)])
  output=tmp_path/'envoy.yaml';output.write_text(yaml.safe_dump(render_envoy(args)));output.chmod(0o644)
  try:
    runtime.workers.start(2)
    with envoy({'port':port,'output':output}):
      assert runtime.run('read')['transport']['http_status']==200
      assert runtime.run('pii')['transport']['receipt']['request_redacted']
      assert runtime.run('delete')['transport']['http_status']==403
      with httpx.Client(timeout=10,trust_env=False) as client:
        request,_=runtime.signed_request(client,'read')
        assert client.send(request).status_code==200
        old=runtime.workers.status()['replicas'][0]['pid'];os.kill(old,signal.SIGKILL)
        wait_for(lambda:runtime.workers.status()['state']=='healthy' and runtime.workers.status()['replicas'][0]['pid']!=old)
        time.sleep(1.5)
        assert client.send(request).status_code==403
        policy=runtime.policy();policy['rules']['notes.read']='block';runtime.apply(policy)
        for _ in range(6):assert runtime.run('read')['transport']['http_status']==403
        policy=runtime.policy();policy['mode']='mirror';runtime.apply(policy)
        event=runtime.run('read')
        assert event['transport']['http_status']==200 and not event['enforcement_applied']
        policy=runtime.policy();policy['mode']='inline';runtime.apply(policy)
        runtime.workers.stop();request,_=runtime.signed_request(client,'read');count=len(destination.receipts)
        assert client.send(request).status_code>=500 and len(destination.receipts)==count
      assert 'alex@example.com' not in str(runtime.store.events())
  finally:
    runtime.workers.stop();destination.shutdown();destination.server_close()


def test_console_lifecycle_resize_and_real_rollback(tmp_path,monkeypatch):
  import asyncio
  import socket
  from asr_proxy.console import runtime as runtime_module
  destination=create_destination(0)
  monkeypatch.setattr(runtime_module,'create_destination',lambda:destination)
  runtime=Runtime(tmp_path/'managed')
  config=runtime.network.current();config['listen_port']=free_port();runtime.store.set('network',config)
  original_render=runtime.network.render
  def render(config):
    result=original_render(config)
    for cluster in result['static_resources']['clusters']:
      if cluster['name']!='trapdefense_inspector':
        cluster['load_assignment']['endpoints'][0]['lb_endpoints'][0]['endpoint']['address']['socket_address']['port_value']=destination.server_port
    return result
  monkeypatch.setattr(runtime.network,'render',render)
  async def exercise():
    try:
      await runtime.start()
      assert (await asyncio.to_thread(runtime.run,'read'))['transport']['http_status']==200
      await asyncio.to_thread(runtime.inspector_control,'apply',2)
      assert len(runtime.workers.status()['replicas'])==2
      assert (await asyncio.to_thread(runtime.run,'pii'))['transport']['receipt']['request_redacted']
      await asyncio.to_thread(runtime.inspector_control,'apply',1)
      with socket.socket() as occupied:
        occupied.bind(('127.0.0.1',18104));occupied.listen()
        with pytest.raises(ValueError):await asyncio.to_thread(runtime.inspector_control,'apply',4)
      assert runtime.store.get('inspectors')['replicas']==1
      assert (await asyncio.to_thread(runtime.run,'read'))['transport']['http_status']==200
      await asyncio.to_thread(runtime.inspector_control,'apply',4)
      assert len(runtime.workers.status()['replicas'])==4
      assert (await asyncio.to_thread(runtime.run,'delete'))['transport']['http_status']==403
      await asyncio.to_thread(runtime.inspector_control,'stop')
      assert runtime.workers.status()['state']=='stopped'
      async with httpx.AsyncClient(timeout=8,trust_env=False) as client:
        request,_=runtime.signed_request(client,'read')
        assert (await client.send(request)).status_code>=500
    finally:await runtime.stop()
  asyncio.run(exercise())
